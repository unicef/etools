import time

from django.db import IntegrityError, transaction
from django.utils.encoding import force_text

from carto.exceptions import CartoException
from carto.sql import SQLClient
from celery.utils.log import get_task_logger

from etools.applications.locations.auth import EtoolsCartoNoAuthClient
from etools.applications.locations.models import CartoDBTable, Location, LocationRemapHistory
from etools.applications.partners.models import Intervention
from etools.applications.reports.models import AppliedIndicator
from etools.applications.t2f.models import TravelActivity
from etools.applications.activities.models import Activity
from etools.applications.action_points.models import ActionPoint
from django.contrib.contenttypes.models import ContentType
from etools.config.celery import app

logger = get_task_logger(__name__)


def create_location(pcode, carto_table, parent, parent_instance,
                    remapped_old_pcode, site_name, row, sites_not_added,
                    sites_created, sites_updated, sites_remapped):
    try:
        location = None
        remapped_location = None
        if remapped_old_pcode is not None:
            try:
                # check if the remapped location exists in the database
                remapped_location = Location.objects.get(p_code=remapped_old_pcode)
            except Location.DoesNotExist:
                # if remapped_old_pcode is set(passed validation), but the remapped location is not found in the
                # list of the active locations(`Location.objects`), it means that the location was already remapped.
                # continue with updating the `main` location, and ignore the remap.
                location = Location.objects.get(p_code=pcode)
        else:
            location = Location.objects.get(p_code=pcode)

    except Location.MultipleObjectsReturned:
        logger.warning("Multiple locations found for: {}, {} ({})".format(
            carto_table.location_type, site_name, pcode
        ))
        sites_not_added += 1
        return False, sites_not_added, sites_created, sites_updated, sites_remapped

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
            return False, sites_not_added, sites_created, sites_updated, sites_remapped

        if 'Point' in row['the_geom']:
            create_args['point'] = row['the_geom']
        else:
            create_args['geom'] = row['the_geom']

        sites_created += 1
        try:
            location = Location.objects.create(**create_args)
        except IntegrityError:
            logger.exception('Error while creating location: %s', site_name)

        logger.info('{}: {} ({})'.format(
            'Added',
            location.name,
            carto_table.location_type.name
        ))

        if remapped_location is not None:
            remapped_location.is_active = False
            remapped_location.save()

            sites_remapped += 1
            logger.info('{}: {} ({})'.format(
                'Remapped',
                remapped_location.name,
                carto_table.location_type.name
            ))

            # remap related entities and save the location remap history
            # interventions
            ctp = ContentType.objects.get(app_label='partners', model='intervention')
            # for intervention in Intervention.objects.filter(????):
            for intervention in Intervention.objects.all():
                if intervention.flat_locations.get(id=remapped_location.id):
                    LocationRemapHistory.objects.create(
                        old_location=remapped_location,
                        new_location=location,
                        content_type=ctp,
                        object_id=intervention.id,
                    )
                    intervention.flat_locations.remove(remapped_location)
                    intervention.flat_locations.add(location)
                    # TODO: logs

            # intervention indicators
            ctp = ContentType.objects.get(app_label='reports', model='appliedindicator')
            # for appliedindicator in AppliedIndicator.objects.filter(????):
            for appliedindicator in AppliedIndicator.objects.all():
                if appliedindicator.locations.get(id=remapped_location.id):
                    LocationRemapHistory.objects.create(
                        old_location=remapped_location,
                        new_location=location,
                        content_type=ctp,
                        object_id=appliedindicator.id,
                    )
                    appliedindicator.locations.remove(remapped_location)
                    appliedindicator.locations.add(location)
                    # TODO: logs

            # travel activities
            ctp = ContentType.objects.get(app_label='t2f', model='travelactivity')
            # for travelactivity in TravelActivity.objects.filter(????):
            for travelactivity in TravelActivity.objects.all():
                if travelactivity.locations.get(id=remapped_location.id):
                    LocationRemapHistory.objects.create(
                        old_location=remapped_location,
                        new_location=location,
                        content_type=ctp,
                        object_id=travelactivity.id,
                    )
                    travelactivity.locations.remove(remapped_location)
                    travelactivity.locations.add(location)
                    # TODO: logs

            # activities
            ctp = ContentType.objects.get(app_label='activities', model='activity')
            # for activity in Activity.objects.filter(????):
            for activity in Activity.objects.all():
                if activity.locations.get(id=remapped_location.id):
                    LocationRemapHistory.objects.create(
                        old_location=remapped_location,
                        new_location=location,
                        content_type=ctp,
                        object_id=activity.id,
                    )
                    activity.locations.remove(remapped_location)
                    activity.locations.add(location)
                    # TODO: logs

            ctp = ContentType.objects.get(app_label='action_points', model='actionpoint')
            for actionpoint in ActionPoint.get(location__id=remapped_location.id):
                LocationRemapHistory.objects.create(
                    old_location=remapped_location,
                    new_location=location,
                    content_type=ctp,
                    object_id=actionpoint.id,
                )
                actionpoint.location.id=location.id
                # TODO: logs

        return True, sites_not_added, sites_created, sites_updated, sites_remapped

    else:
        if not row['the_geom']:
            return False, sites_not_added, sites_created, sites_updated, sites_remapped

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
            return False, sites_not_added, sites_created, sites_updated, sites_remapped

        sites_updated += 1
        logger.info('{}: {} ({})'.format(
            'Updated',
            location.name,
            carto_table.location_type.name
        ))

        return True, sites_not_added, sites_created, sites_updated, sites_remapped


@app.task
def update_sites_from_cartodb(carto_table_pk):

    try:
        carto_table = CartoDBTable.objects.get(pk=carto_table_pk)
    except CartoDBTable.DoesNotExist:
        logger.exception('Cannot retrieve CartoDBTable with pk: %s', carto_table_pk)
        return

    auth_client = EtoolsCartoNoAuthClient(base_url="https://{}.carto.com/".format(carto_table.domain))
    sql_client = SQLClient(auth_client)
    sites_created = sites_updated = sites_remapped = sites_not_added = 0

    # query for cartodb
    qry = ''
    rows = []
    cartodb_id_col = 'cartodb_id'

    try:
        query_row_count = sql_client.send('select count(*) from {}'.format(carto_table.table_name))
        row_count = query_row_count['rows'][0]['count']

        # do not spam Carto with requests, wait 1 second
        time.sleep(1)
        query_max_id = sql_client.send('select MAX({}) from {}'.format(cartodb_id_col, carto_table.table_name))
        max_id = query_max_id['rows'][0]['max']
    except CartoException:
        logger.exception("Cannot fetch pagination prequisites from CartoDB for table {}".format(
            carto_table.table_name
        ))
        return "Table name {}: {} sites created, {} sites updated, {} sites remapped, {} sites skipped".format(
            carto_table.table_name, 0, 0, 0, 0
        )

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

    try:
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
                return
    except CartoException:
        logger.exception("CartoDB exception occured")
    else:
        # wrap Location tree updates in a transaction, to prevent an invalid tree state due to errors
        with transaction.atomic():
            # disable tree 'generation' during single row updates, rebuild the tree after.
            # this should prevent errors happening (probably)due to invalid intermediary tree state
            with Location.objects.disable_mptt_updates():
                # if we have a remap table, fetch it's content and validate it
                if carto_table.remap_table_name:
                    remapped_pcode_pairs = []
                    # get the list of the new Pcodes from the Carto data
                    new_pcodes = [str(row[carto_table.pcode_col]) for row in sites['rows']]

                    try:
                        remap_qry = 'select old_pcode::text, new_pcode::text from {}'.format(
                            carto_table.remap_table_name)
                        remapped_pcode_pairs = sql_client.send(remap_qry)['rows']
                    except CartoException:
                        logger.exception("CartoDB exception occured on the remap table query")
                        return
                    else:
                        validation_failed = False

                        # get the list of the existing Pcodes and previous Pcodes from the database
                        database_pcodes = set()
                        for row in Location.all_locations.filter(gateway=carto_table.location_type).values('p_code'):
                            database_pcodes.add(row['p_code'])
                        database_pcodes = list(database_pcodes)

                        # test
                        # remapped_pcode_pairs.append({'new_pcode': 'testn1', 'old_pcode': 'testo1'})
                        # remapped_pcode_pairs.append({'new_pcode': 'testn2', 'old_pcode': 'testo2'})

                        # validate remap table
                        bad_old_pcodes = []
                        bad_new_pcodes = []
                        for remap_row in remapped_pcode_pairs:
                            # check for non-existing remap pcodes in the database
                            if remap_row['old_pcode'] not in database_pcodes:
                                bad_old_pcodes.append(remap_row['old_pcode'])
                            # check for non-existing remap pcodes in the Carto dataset
                            if remap_row['new_pcode'] not in new_pcodes:
                                bad_new_pcodes.append(remap_row['new_pcode'])

                        if len(bad_old_pcodes) > 0:
                            logger.warning(
                                "Invalid old_pcode found in the remap table: {}".format(','.join(bad_old_pcodes)))
                            validation_failed = True

                        if len(bad_new_pcodes) > 0:
                            logger.warning(
                                "Invalid new_pcode found in the remap table: {}".format(','.join(bad_new_pcodes)))
                            validation_failed = True

                        if validation_failed is True:
                            return

                for row in rows:
                    pcode = str(row[carto_table.pcode_col]).strip()
                    site_name = row[carto_table.name_col]

                    if not site_name or site_name.isspace():
                        logger.warning("No name for location with PCode: {}".format(pcode))
                        sites_not_added += 1
                        continue

                    parent = None
                    parent_code = None
                    parent_instance = None

                    # attempt to reference the parent of this location
                    if carto_table.parent_code_col and carto_table.parent:
                        msg = None
                        parent = carto_table.parent.__class__
                        parent_code = row[carto_table.parent_code_col]
                        try:
                            parent_instance = Location.objects.get(p_code=parent_code)
                        except Location.MultipleObjectsReturned:
                            msg = "Multiple locations found for parent code: {}".format(
                                parent_code
                            )
                        except Location.DoesNotExist:
                            msg = "No locations found for parent code: {}".format(
                                parent_code
                            )
                        except Exception as exp:
                            msg = force_text(exp)

                        if msg is not None:
                            logger.warning(msg)
                            sites_not_added += 1
                            continue

                    # check if the Carto location should be remapped to an old location
                    remapped_old_pcode = None
                    if carto_table.remap_table_name and len(remapped_pcode_pairs) > 0:
                        for remap_row in remapped_pcode_pairs:
                            if pcode == remap_row['new_pcode']:
                                remapped_old_pcode = remap_row['old_pcode']

                    # print(remapped_old_pcode)
                    # create the actual location or retrieve existing based on type and code
                    succ, sites_not_added, sites_created, sites_updated, sites_remapped = create_location(
                        pcode, carto_table,
                        parent, parent_instance, remapped_old_pcode,
                        site_name, row,
                        sites_not_added, sites_created,
                        sites_updated, sites_remapped)

            Location.objects.rebuild()

    return "Table name {}: {} sites created, {} sites updated, {} sites remapped, {} sites skipped".format(
        carto_table.table_name, sites_created, sites_updated, sites_remapped, sites_not_added)
