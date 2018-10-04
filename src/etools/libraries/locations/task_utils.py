import time

from carto.exceptions import CartoException
from celery.utils.log import get_task_logger
from collections import defaultdict

from django.db import IntegrityError
from django.db.models import Count

from unicef_locations.models import Location, LocationRemapHistory

from etools.applications.partners.models import Intervention
from etools.applications.reports.models import AppliedIndicator
from etools.applications.t2f.models import TravelActivity
from etools.applications.activities.models import Activity
from etools.applications.action_points.models import ActionPoint


logger = get_task_logger(__name__)


def get_cartodb_locations(sql_client, carto_table):
    rows = []
    cartodb_id_col = 'cartodb_id'

    try:
        query_row_count = sql_client.send('select count(*) from {}'.format(carto_table.table_name))
        row_count = query_row_count['rows'][0]['count']

        # do not spam Carto with requests, wait 1 second
        time.sleep(1)
        query_max_id = sql_client.send('select MAX({}) from {}'.format(cartodb_id_col, carto_table.table_name))
        max_id = query_max_id['rows'][0]['max']
    except CartoException:  # pragma: no-cover
        logger.exception("Cannot fetch pagination prequisites from CartoDB for table {}".format(
            carto_table.table_name
        ))
        return False, []

    offset = 0
    limit = 100

    # failsafe in the case when cartodb id's are too much off compared to the nr. of records
    if max_id > (5 * row_count):
        limit = max_id + 1
        logger.warning("The CartoDB primary key seemf off, pagination is not possible")

    if carto_table.parent_code_col and carto_table.parent:
        qry = 'select st_AsGeoJSON(the_geom) as the_geom, {}, {}, {} from {}'.format(
            carto_table.name_col,
            carto_table.pcode_col,
            carto_table.parent_code_col,
            carto_table.table_name)
    else:
        qry = 'select st_AsGeoJSON(the_geom) as the_geom, {}, {} from {}'.format(
            carto_table.name_col,
            carto_table.pcode_col,
            carto_table.table_name)

    while offset <= max_id:
        paged_qry = qry + ' WHERE {} > {} AND {} <= {}'.format(
            cartodb_id_col,
            offset,
            cartodb_id_col,
            offset + limit
        )
        logger.info('Requesting rows between {} and {} for {}'.format(
            offset,
            offset + limit,
            carto_table.table_name
        ))

        # do not spam Carto with requests, wait 1 second
        time.sleep(1)
        sites = sql_client.send(paged_qry)
        rows += sites['rows']
        offset += limit

        if 'error' in sites:
            # it seems we can have both valid results and error messages in the same CartoDB response
            logger.exception("CartoDB API error received: {}".format(sites['error']))
            # When this error occurs, we receive truncated locations, probably it's better to interrupt the import
            return False, []

    return True, rows


def validate_remap_table(database_pcodes, new_carto_pcodes, carto_table, sql_client):  # pragma: no-cover
    remapped_pcode_pairs = []
    remap_old_pcodes = []
    remap_new_pcodes = []
    remap_table_valid = True

    if carto_table.remap_table_name:
        try:
            remap_qry = 'select old_pcode::text, new_pcode::text from {}'.format(
                carto_table.remap_table_name)
            remapped_pcode_pairs = sql_client.send(remap_qry)['rows']
        except CartoException:  # pragma: no-cover
            logger.exception("CartoDB exception occured on the remap table query")
            remap_table_valid = False
        else:
            # validate remap table
            bad_old_pcodes = []
            bad_new_pcodes = []
            for remap_row in remapped_pcode_pairs:
                if 'old_pcode' not in remap_row or 'new_pcode' not in remap_row:
                    return False, remapped_pcode_pairs, remap_old_pcodes, remap_new_pcodes

                remap_old_pcodes.append(remap_row['old_pcode'])
                remap_new_pcodes.append(remap_row['new_pcode'])

                # check for non-existing remap pcodes in the database
                if remap_row['old_pcode'] not in database_pcodes:
                    bad_old_pcodes.append(remap_row['old_pcode'])
                # check for non-existing remap pcodes in the Carto dataset
                if remap_row['new_pcode'] not in new_carto_pcodes:
                    bad_new_pcodes.append(remap_row['new_pcode'])

            if len(bad_old_pcodes) > 0:
                logger.exception(
                    "Invalid old_pcode found in the remap table: {}".format(','.join(bad_old_pcodes)))
                remap_table_valid = False

            if len(bad_new_pcodes) > 0:
                logger.exception(
                    "Invalid new_pcode found in the remap table: {}".format(','.join(bad_new_pcodes)))
                remap_table_valid = False

    return remap_table_valid, remapped_pcode_pairs, remap_old_pcodes, remap_new_pcodes


def duplicate_pcodes_exist(database_pcodes, new_carto_pcodes, remap_old_pcodes):  # pragma: no-cover
    duplicates_found = False
    temp = {}
    duplicate_database_pcodes = []
    for database_pcode in database_pcodes:
        if database_pcode in temp:
            duplicate_database_pcodes.append(database_pcode)
        temp[database_pcode] = 1

    if duplicate_database_pcodes:
        logger.exception("Duplicates found in the existing database pcodes: {}".
                         format(','.join(duplicate_database_pcodes)))
        duplicates_found = True

    temp = {}
    duplicate_carto_pcodes = []
    for new_carto_pcode in new_carto_pcodes:
        if new_carto_pcode in temp:
            duplicate_carto_pcodes.append(new_carto_pcode)
        temp[new_carto_pcode] = 1

    if duplicate_carto_pcodes:
        logger.exception("Duplicates found in the new CartoDB pcodes: {}".
                         format(','.join(duplicate_database_pcodes)))
        duplicates_found = True

    temp = {}
    duplicate_remap_old_pcodes = []
    for remap_old_pcode in remap_old_pcodes:
        if remap_old_pcode in temp:
            duplicate_remap_old_pcodes.append(remap_old_pcode)
        temp[remap_old_pcode] = 1

    if duplicate_remap_old_pcodes:
        logger.exception("Duplicates found in the remap table `old pcode` column: {}".
                         format(','.join(duplicate_remap_old_pcodes)))
        duplicates_found = True

    return duplicates_found


def get_location_ids_in_use(location_ids):
    """
    :param location_ids: list of location ids to check
    :return location_ids_in_use: the input reduced to locations in use
    """
    location_ids_in_use = []

    for intervention in Intervention.objects.all():
        location_ids_in_use += [l.id for l in intervention.flat_locations.filter(id__in=location_ids)]

    for indicator in AppliedIndicator.objects.all():
        location_ids_in_use += [l.id for l in indicator.locations.filter(id__in=location_ids)]

    for travelactivity in TravelActivity.objects.all():
        location_ids_in_use += [l.id for l in travelactivity.locations.filter(id__in=location_ids)]

    for activity in Activity.objects.all():
        location_ids_in_use += [l.id for l in activity.locations.filter(id__in=location_ids)]

    location_ids_in_use += [a.location_id for a in ActionPoint.objects.filter(location__in=location_ids).distinct()]

    return list(set(location_ids_in_use))


def create_location(pcode, carto_table, parent, parent_instance, remapped_old_pcodes, site_name,
                    row, sites_not_added, sites_created, sites_updated, sites_remapped):

    results = None
    try:
        location = None
        remapped_locations = None
        if remapped_old_pcodes:
            # check if the remapped location exists in the database
            remapped_locations = Location.objects.filter(p_code__in=list(remapped_old_pcodes))

            if not remapped_locations:
                # if remapped_old_pcodes are set and passed validations, but they are not found in the
                # list of the active locations(`Location.objects`), it means that they were already remapped.
                # in this case update the `main` location, and ignore the remap.
                location = Location.objects.get(p_code=pcode)
        else:
            location = Location.objects.get(p_code=pcode)

    except Location.MultipleObjectsReturned:
        logger.warning("Multiple locations found for: {}, {} ({})".format(
            carto_table.location_type, site_name, pcode
        ))
        sites_not_added += 1
        return False, sites_not_added, sites_created, sites_updated, sites_remapped, results

    except Location.DoesNotExist:
        pass

    if not location:
        # try to create the location
        create_args = {
            'p_code': pcode,
            'gateway': carto_table.location_type,
            'name': site_name
        }
        if parent and parent_instance:
            create_args['parent'] = parent_instance

        if not row['the_geom']:
            sites_not_added += 1
            return False, sites_not_added, sites_created, sites_updated, sites_remapped, results

        if 'Point' in row['the_geom']:
            create_args['point'] = row['the_geom']
        else:
            create_args['geom'] = row['the_geom']

        try:
            location = Location.objects.create(**create_args)
            sites_created += 1
        except IntegrityError:
            logger.exception('Error while creating location: %s', site_name)
            sites_not_added += 1
            return False, sites_not_added, sites_created, sites_updated, sites_remapped, results

        logger.info('{}: {} ({})'.format(
            'Added',
            location.name,
            carto_table.location_type.name
        ))

        results = []
        if remapped_locations:
            for remapped_location in remapped_locations:
                remapped_location.is_active = False
                remapped_location.save()

                sites_remapped += 1
                logger.info('{}: {} ({})'.format(
                    'Remapped',
                    remapped_location.name,
                    carto_table.location_type.name
                ))

                results.append((location.id, remapped_location.id))
        else:
            results = [(location.id, None)]

        return True, sites_not_added, sites_created, sites_updated, sites_remapped, results

    else:
        if not row['the_geom']:
            return False, sites_not_added, sites_created, sites_updated, sites_remapped, results

        # names can be updated for existing locations with the same code
        location.name = site_name

        if 'Point' in row['the_geom']:
            location.point = row['the_geom']
        else:
            location.geom = row['the_geom']

        if parent and parent_instance:
            logger.info("Updating parent:{} for location {}".format(parent_instance, location))
            location.parent = parent_instance
        else:
            location.parent = None

        try:
            location.save()
        except IntegrityError:
            logger.exception('Error while saving location: %s', site_name)
            return False, sites_not_added, sites_created, sites_updated, sites_remapped, results

        sites_updated += 1
        logger.info('{}: {} ({})'.format(
            'Updated',
            location.name,
            carto_table.location_type.name
        ))

        results = [(location.id, None)]
        return True, sites_not_added, sites_created, sites_updated, sites_remapped, results


def update_model_locations(remapped_locations, model, related_object, related_property, multiples):

    print("in update model", model, remapped_locations)
    print("in update multiples", model, multiples)
    random_object = model.objects.first()
    if random_object:
        handled_related_objects = []
        ThroughModel = getattr(random_object, related_property).through
        # clean up multiple remaps
        for loc in remapped_locations:
            print("in update model - loc in remapped", loc)
            old_location_id = loc[1]
            new_location_id = loc[0]
            if len(multiples[new_location_id]) > 1:
                # print('were getting in here yay!', multiples)
                grouped_magic = ThroughModel.objects.filter(location__in=multiples[new_location_id]).\
                    values(related_object).annotate(object_count=Count(related_object)).\
                    filter(object_count__gt=1)

                if model == Intervention:
                    print("stuff(m)", related_object, multiples[new_location_id])
                    print(grouped_magic)

                print("handled objects", handled_related_objects)

                for record in grouped_magic:
                    print("record", record)
                    related_object_id = record.get(related_object)
                    check_record = (related_object_id, new_location_id)
                    if check_record not in handled_related_objects:
                        print("adding to handle", check_record)
                        handled_related_objects.append(check_record)
                    else:
                        filter_args = {related_object:related_object_id, "location":old_location_id}
                        print("deleting duplicate by cond ", filter_args)
                        ThroughModel.objects.filter(**filter_args).delete()

        # update through table only after it was cleaned up from duplicates
        for loc in remapped_locations:
            ThroughModel.objects.filter(location=loc[1]).update(location=loc[0])


def save_location_remap_history(imported_locations):
    '''
    :param imported_locations: set of (new_location_id, remapped_location_id) tuples, where remapped_location can be None
    :return:
    '''

    if not imported_locations:
        return
    remapped_locations = set([tp for tp in imported_locations if tp[1]])
    if not remapped_locations:
        return

    multiples = defaultdict(list)
    for loc_tp in remapped_locations:
        multiples[loc_tp[0]].append(loc_tp[1])

    print(multiples)
    for model, related_object, related_property in [(AppliedIndicator, "appliedindicator", "locations"),
                                            (TravelActivity, "travelactivity", "locations"),
                                            (Activity, "activity", "locations"),
                                            (Intervention, "intervention", "flat_locations")]:
        update_model_locations(remapped_locations, model, related_object, related_property, multiples)

    # action points
    for loc_tp in remapped_locations:
        ActionPoint.objects.filter(location=loc_tp[1]).update(location=loc_tp[0])

    for loc_tp in remapped_locations:
        LocationRemapHistory.objects.create(
            old_location=Location.all_locations.get(id=loc_tp[1]),
            new_location=Location.all_locations.get(id=loc_tp[0]),
            comments="Remapped location id {} to id {}".format(loc_tp[1], loc_tp[0])
        )


def save_location_remap_history_2(imported_locations):
    '''
    :param imported_locations: set of (new_location_id, remapped_location_id) tuples, where remapped_location can be None
    :return:
    '''

    if not imported_locations:
        return

    remapped_locations = [tp for tp in imported_locations if tp[1]]

    # remapped_locations = {loc[1]: loc[0] for loc in imported_locations if loc[1]}

    if not remapped_locations:
        return

    # Interventions
    random_intervention = Intervention.objects.first()
    if random_intervention:
        InterventionLocationThrough = random_intervention.flat_locations.through
        # loc:  {111:1, 111:2},  interv: {11:1, 11:2, 12:2} ->
        #    {11: 111} ->
        #    {11: 111} -> ERR, {12: 111} -> ?


        for loc in remapped_locations:
            # updated_locs = InterventionLocationThrough.objects.filter(location=loc[0])
            InterventionLocationThrough.objects.filter(location=loc[1]).update(location=loc[0])

    '''
    for model in [AppliedIndicator, TravelActivity, Activity]:
        update_model_locations(remapped_locations, model)
    '''

    # action points
    for loc_tp in remapped_locations:
        ActionPoint.objects.filter(location=loc_tp[1]).update(location=loc_tp[0])

    # also insert a row without related content in the remap table, for the purpose of keeping history
    for new_loc, old_loc in remapped_locations:
        LocationRemapHistory.objects.create(
            old_location=Location.objects.all_locations().get(pk=old_loc),
            new_location=Location.objects.all_locations().get(pk=new_loc),
            comments="Remapped location id {} to id {}".format(old_loc, new_loc)
        )

def save_location_remap_history_old(imported_locations):
    '''
    :param imported_locations: set of (new_location, remapped_location) tuples, where remapped_location can be None
    :return:
    '''

    remapped_locations = {loc[1]: loc[0] for loc in imported_locations if loc[1]}

    if not remapped_locations:
        return

    # remap related entities to the newly added locations
    # interventions
    for intervention in Intervention.objects.filter(flat_locations__in=[*remapped_locations]).distinct():
        print("intervention {}".format(intervention.id))
        print ([*remapped_locations])
        print (intervention.flat_locations)
        for remapped_location in intervention.flat_locations(manager='all_locations').filter(id__in=[*remapped_locations]):
            print("location {}".format(remapped_location.id))
            new_location = remapped_locations.get(remapped_location.id)
            intervention.flat_locations.remove(remapped_location)
            intervention.flat_locations.add(new_location)
        print("\n")

    # intervention indicators
    for appliedindicator in AppliedIndicator.objects.filter(locations__in=[*remapped_locations]).distinct():
        for remapped_location in appliedindicator.locations.filter(id__in=[*remapped_locations]):
            new_location = remapped_locations.get(remapped_location.id)
            appliedindicator.locations.remove(remapped_location)
            appliedindicator.locations.add(new_location)

    # travel activities
    for travelactivity in TravelActivity.objects.filter(locations__in=[*remapped_locations]).distinct():
        for remapped_location in travelactivity.locations.filter(id__in=[*remapped_locations]):
            new_location = remapped_locations.get(remapped_location.id)
            travelactivity.locations.remove(remapped_location)
            travelactivity.locations.add(new_location)

    # activities
    for activity in Activity.objects.filter(locations__in=[*remapped_locations]).distinct():
        for remapped_location in activity.locations.filter(id__in=[*remapped_locations]):
            new_location = remapped_locations.get(remapped_location.id)
            activity.locations.remove(remapped_location)
            activity.locations.add(new_location)

    # action points
    for actionpoint in ActionPoint.objects.filter(location__in=[*remapped_locations]).distinct():
        new_location = remapped_locations.get(actionpoint.location.id)
        actionpoint.location.id = new_location
        actionpoint.save()

    # also insert a row without related content in the remap table, for the purpose of keeping history
    for old_loc, new_loc in remapped_locations.items():
        LocationRemapHistory.objects.create(
            old_location=Location.objects.all_locations().get(pk=old_loc),
            new_location=Location.objects.all_locations().get(pk=new_loc),
            comments="Remapped location id {} to id {}".format(old_loc, new_loc)
        )
