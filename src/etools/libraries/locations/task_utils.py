import time
from collections import defaultdict

from django.db import IntegrityError
from django.db.models import Count

from carto.exceptions import CartoException
from celery.utils.log import get_task_logger
from unicef_locations.models import Location, LocationRemapHistory

from etools.applications.action_points.models import ActionPoint
from etools.applications.activities.models import Activity
from etools.applications.partners.models import Intervention
from etools.applications.reports.models import AppliedIndicator
from etools.applications.t2f.models import TravelActivity

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
        try:
            sites = sql_client.send(paged_qry)
        except CartoException:  # pragma: no-cover
            logger.exception("CartoDB API pagination failed at offset: {}".format(offset))
            retried_row = retry_failed_query(sql_client, paged_qry, offset)
            if retried_row:
                rows += retried_row
                offset += limit
            else:
                # can not continue if we have missing pages..
                return False, []
        else:
            if 'error' in sites:
                # it seems we can have both valid results and error messages in the same CartoDB response
                # When this occurs, we receive truncated locations, interrupt the import due to incomplete data
                logger.exception("CartoDB API error received: {}".format(sites['error']))
                return False, []
            else:
                rows += sites['rows']
                offset += limit

    return True, rows


def retry_failed_query(sql_client, failed_query, offset):
    """
    Retry a timed-out CartoDB query
    :param sql_client:
    :param failed_query:
    :param offset:
    :return:
    """

    retries = 0
    logger.warning('Retrying table page at offset {}'.format(offset))
    while retries < 5:
        time.sleep(1)
        retries += 1
        try:
            sites = sql_client.send(failed_query)
        except CartoException:
            if retries < 5:
                logger.warning('Retrying again table page at offset {}'.format(offset))
        else:
            if 'error' in sites:
                return False
            else:
                return sites['rows']
    return False


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
    """
    :param pcode: pcode of the new/updated location
    :param carto_table:
    :param parent:
    :param parent_instance:
    :param remapped_old_pcodes: list of old pcodes which will be replaced by the new `pcode`
    :param site_name:
    :param row: the new location data as received from CartoDB
    :param sites_not_added:
    :param sites_created:
    :param sites_updated:
    :param sites_remapped:
    :return:
    """

    logger.info('{}: {} ({}){}'.format(
        'Importing location ',
        pcode,
        carto_table.location_type.name,
        ", remapped pcodes: {}".format(",".join(remapped_old_pcodes)) if remapped_old_pcodes else ""
    ))

    results = None
    try:
        location = None
        remapped_locations = None
        if remapped_old_pcodes:
            # check if the remapped location exists in the database(ACTIVE locations only)
            remapped_locations = Location.objects.filter(p_code__in=list(remapped_old_pcodes))

            if not remapped_locations.exists():
                # if remapped_old_pcodes are valid, but they are not found in the  list of the active locations
                # (`Location.objects`), it means that they were already remapped.
                # in this case update the `main` location, and ignore the remap.
                location = Location.objects.all_locations().get(p_code=pcode)
        else:
            location = Location.objects.all_locations().get(p_code=pcode)

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

    random_object = model.objects.first()
    if random_object:
        handled_related_objects = []
        ThroughModel = getattr(random_object, related_property).through
        # clean up multiple remaps
        for new_location_id, old_location_id in remapped_locations:
            """
            Clean up `multiple/duplicate remaps` from the through table.
            This step is necessary because a new location can replace multiple old locations during the remap, and the
            through table constraints disallow duplicates appearing due to multiple old locations being replaced by the
            same new location.
            """

            if len(multiples[new_location_id]) > 1:
                # it seems Django can do the wanted grouping only if we pass the counted column in `values()`
                # the result contains the related ref id and the nr. of duplicates, ex.:
                # <QuerySet [{'intervention': 27, 'object_count': 2}, {'intervention': 104, 'object_count': 2}]>
                grouped_magic = ThroughModel.objects.filter(location__in=multiples[new_location_id]).\
                    values(related_object).annotate(object_count=Count(related_object)).\
                    filter(object_count__gt=1)

                for record in grouped_magic:
                    related_object_id = record.get(related_object)
                    # create something to check against
                    check_record = (related_object_id, new_location_id)
                    if check_record not in handled_related_objects:
                        handled_related_objects.append(check_record)
                    else:
                        # construct the delete query
                        # all the `duplicate remaps` except the one skipped with the `check_record` should be picked up
                        filter_args = {related_object: related_object_id, "location": old_location_id}
                        ThroughModel.objects.filter(**filter_args).delete()

        # update through table only after it was cleaned up from duplicates
        for loc in remapped_locations:
            ThroughModel.objects.filter(location=loc[1]).update(location=loc[0])


def save_location_remap_history(imported_locations):
    """
    :param imported_locations: set of (new_location_id, remapped_location_id) tuples, where remapped_location can be None
    :return:
    """

    if not imported_locations:
        return
    remapped_locations = set([tp for tp in imported_locations if tp[1]])
    if not remapped_locations:
        return

    multiples = defaultdict(list)
    for loc_tp in remapped_locations:
        multiples[loc_tp[0]].append(loc_tp[1])

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
            old_location=Location.objects.all_locations().get(id=loc_tp[1]),
            new_location=Location.objects.all_locations().get(id=loc_tp[0]),
            comments="Remapped location id {} to id {}".format(loc_tp[1], loc_tp[0])
        )
