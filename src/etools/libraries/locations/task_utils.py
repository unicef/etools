from collections import defaultdict

from django.db import IntegrityError
from django.db.models import Count

from celery.utils.log import get_task_logger
from unicef_locations.models import Location, LocationRemapHistory

from etools.applications.action_points.models import ActionPoint
from etools.applications.activities.models import Activity
from etools.applications.partners.models import Intervention
from etools.applications.reports.models import AppliedIndicator
from etools.applications.t2f.models import TravelActivity

logger = get_task_logger(__name__)


def validate_remap_table(remapped_pcode_pairs, database_pcodes, new_pcodes, ):  # pragma: no-cover
    remapped_old_pcodes = []
    remapped_new_pcodes = []
    remap_table_valid = True

    # validate remap table
    bad_old_pcodes = []
    bad_new_pcodes = []
    for remap_row in remapped_pcode_pairs:
        if 'old_pcode' not in remap_row or 'new_pcode' not in remap_row:
            return False, remapped_pcode_pairs, remapped_old_pcodes, remapped_new_pcodes

        remapped_old_pcodes.append(remap_row['old_pcode'])
        remapped_new_pcodes.append(remap_row['new_pcode'])

        # check for non-existing remap pcodes in the database
        if remap_row['old_pcode'] not in database_pcodes:
            bad_old_pcodes.append(remap_row['old_pcode'])
        # check for non-existing remap pcodes in the Carto dataset
        if remap_row['new_pcode'] not in new_pcodes:
            bad_new_pcodes.append(remap_row['new_pcode'])

    if len(bad_old_pcodes) > 0:
        logger.exception(
            "Invalid old_pcode found in the remap table: {}".format(','.join(bad_old_pcodes)))
        remap_table_valid = False

    if len(bad_new_pcodes) > 0:
        logger.exception(
            "Invalid new_pcode found in the remap table: {}".format(','.join(bad_new_pcodes)))
        remap_table_valid = False

    return remap_table_valid, remapped_old_pcodes, remapped_new_pcodes


def duplicate_pcodes_exist(database_pcodes, new_pcodes, remapped_old_pcodes):  # pragma: no-cover
    duplicates_found = False
    temp = {}
    duplicate_database_pcodes = []
    for database_pcode in database_pcodes:
        if database_pcode in temp:
            if database_pcode not in duplicate_database_pcodes:
                duplicate_database_pcodes.append(database_pcode)
        temp[database_pcode] = 1

    if duplicate_database_pcodes:
        logger.exception("Duplicates found in the existing database pcodes: {}".
                         format(','.join(duplicate_database_pcodes)))
        duplicates_found = True

    temp = {}
    duplicate_new_pcodes = []
    for new_pcode in new_pcodes:
        if new_pcode in temp:
            if new_pcode not in duplicate_new_pcodes:
                duplicate_new_pcodes.append(new_pcode)
        temp[new_pcode] = 1

    if duplicate_new_pcodes:
        logger.exception("Duplicates found in the new pcodes: {}".
                         format(','.join(duplicate_new_pcodes)))
        duplicates_found = True

    temp = {}
    duplicate_remapped_old_pcodes = []
    for remap_old_pcode in remapped_old_pcodes:
        if remap_old_pcode in temp:
            duplicate_remapped_old_pcodes.append(remap_old_pcode)
        temp[remap_old_pcode] = 1

    if duplicate_remapped_old_pcodes:
        logger.exception("Duplicates found in the remap table `old pcode` column: {}".
                         format(','.join(duplicate_remapped_old_pcodes)))
        duplicates_found = True

    # if len(remap_new_pcodes) != len(set(remap_new_pcodes)):
    #     logger.info("Duplicates found in the remap table new pcodes(at this point not an issue)")

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


def filter_remapped_locations(remap_row):
    old_location_id = Location.objects.all_locations().get(p_code=remap_row['old_pcode']).id
    return len(get_location_ids_in_use([old_location_id])) > 0


def create_location(pcode, datadef_table, parent, parent_instance, site_name, the_geom,
                    sites_not_added, sites_created, sites_updated):
    """
    :param pcode: pcode of the new/updated location
    :param datadef_table: table that holds the imported datasets properties(CartoDBTable, , etc..)
    :param parent:
    :param parent_instance:
    :param site_name:
    :param row: the new location data as received from CartoDB
    :param sites_not_added:
    :param sites_created:
    :param sites_updated:
    :return:
    """

    logger.info('{}: {} ({})'.format(
        'Importing location',
        pcode,
        datadef_table.location_type.name
    ))

    location = None
    try:
        # TODO: revisit this, maybe include (location name?) carto_table in the check
        # see below at update branch - names can be updated for existing locations with the same code
        location = Location.objects.all_locations().get(p_code=pcode)

    except Location.MultipleObjectsReturned:
        logger.warning("Multiple locations found for: {}, {} ({})".format(
            datadef_table.location_type, site_name, pcode
        ))
        sites_not_added += 1
        return False, sites_not_added, sites_created, sites_updated

    except Location.DoesNotExist:
        pass

    if not location:
        # try to create the location
        create_args = {
            'p_code': pcode,
            'gateway': datadef_table.location_type,
            'name': site_name
        }
        if parent and parent_instance:
            create_args['parent'] = parent_instance

        if not the_geom:
            sites_not_added += 1
            return False, sites_not_added, sites_created, sites_updated

        if 'Point' in the_geom:
            create_args['point'] = the_geom
        else:
            create_args['geom'] = the_geom

        try:
            location = Location.objects.create(**create_args)
            sites_created += 1
        except IntegrityError:
            logger.exception('Error while creating location: %s', site_name)
            sites_not_added += 1
            return False, sites_not_added, sites_created, sites_updated

        logger.info('{}: {} ({})'.format(
            'Added',
            location.name,
            datadef_table.location_type.name
        ))

        return True, sites_not_added, sites_created, sites_updated

    else:
        if not the_geom:
            return False, sites_not_added, sites_created, sites_updated

        # names can be updated for existing locations with the same code
        location.name = site_name
        # TODO: re-confirm if this is not a problem. (assuming that every row in the new data is active)
        location.is_active = True

        if 'Point' in the_geom:
            location.point = the_geom
        else:
            location.geom = the_geom

        if parent and parent_instance:
            logger.info("Updating parent:{} for location {}".format(parent_instance, location))
            location.parent = parent_instance
        else:
            location.parent = None

        try:
            location.save()
        except IntegrityError:
            logger.exception('Error while saving location: %s', site_name)
            return False, sites_not_added, sites_created, sites_updated

        sites_updated += 1
        logger.info('{}: {} ({})'.format(
            'Updated',
            location.name,
            datadef_table.location_type.name
        ))

        return True, sites_not_added, sites_created, sites_updated


def remap_location(carto_table, new_pcode, remapped_pcodes):
    """
    :param carto_table:
    :param new_pcode: pcode the others will be remapped to
    :param remapped_pcodes: pcodes to be remapped and archived/removed

    :return: [(new_location.id, remapped_location.id), ...]
    """

    remapped_locations = Location.objects.all_locations().filter(p_code__in=list(remapped_pcodes))
    if not remapped_locations:
        logger.info('Remapped pcodes: [{}] cannot be found in the database!'.format(",".join(remapped_pcodes)))
        return

    logger.info('Preparing to remap : [{}] to {}'.format(",".join(remapped_pcodes), new_pcode))

    try:
        new_location = Location.objects.all_locations().get(p_code=new_pcode)
        # the approach below is not good - remap should work across location levels, and probably for archived locs too
        # new_location = Location.objects.get(p_code=new_pcode, gateway=carto_table.location_type)
    except Location.MultipleObjectsReturned:
        logger.warning("REMAP: multiple locations found for new pcode: {} ({})".format(
            new_pcode, carto_table.location_type
        ))
        return None
    except Location.DoesNotExist:
        # if the remap destination location does not exist in the DB, we have to create it.
        # the `name`  and `parent` will be updated in the next step of the update process.
        create_args = {
            'p_code': new_pcode,
            'gateway': carto_table.location_type,
            'name': new_pcode   # the name is temporary
        }
        new_location = Location.objects.create(**create_args)

    results = []
    for remapped_location in remapped_locations:
        remapped_location.is_active = False
        remapped_location.save()

        logger.info('Prepared to remap {} to {} ({})'.format(
            remapped_location.p_code,
            new_location.p_code,
            carto_table.location_type.name
        ))

        results.append((new_location.id, remapped_location.id))

    return results


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


def save_location_remap_history(remapped_location_pairs):
    """
    :param remapped_location_pairs: (new_location_id, remapped_location_id) tuples, where remapped_location can be None
    :return:
    """

    if not remapped_location_pairs:
        return
    remapped_locations = set([tp for tp in remapped_location_pairs if tp[1]])
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
