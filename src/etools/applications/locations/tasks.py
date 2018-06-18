import time

from django.db import IntegrityError, transaction
from django.utils.encoding import force_text

from carto.exceptions import CartoException
from carto.sql import SQLClient
from celery.utils.log import get_task_logger

from etools.applications.locations.auth import EtoolsCartoNoAuthClient
from etools.applications.locations.models import CartoDBTable, Location
from etools.config.celery import app

logger = get_task_logger(__name__)


def create_location(pcode, carto_table, parent, parent_instance,
                    site_name, row,
                    sites_not_added, sites_created, sites_updated):
    try:
        location = Location.objects.get(p_code=pcode)

    except Location.MultipleObjectsReturned:
        logger.warning("Multiple locations found for: {}, {} ({})".format(
            carto_table.location_type, site_name, pcode
        ))
        sites_not_added += 1
        return False, sites_not_added, sites_created, sites_updated

    except Location.DoesNotExist:
        # try to create the location
        create_args = {
            'p_code': pcode,
            'gateway': carto_table.location_type,
            'name': site_name
        }
        if parent and parent_instance:
            create_args['parent'] = parent_instance

        if not row['the_geom']:
            return False, sites_not_added, sites_created, sites_updated

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
        return True, sites_not_added, sites_created, sites_updated

    else:

        # names can be updated for existing locations with the same code
        location.name = site_name
        if not row['the_geom']:
            return False, sites_not_added, sites_created, sites_updated

        if 'Point' in row['the_geom']:
            location.point = row['the_geom']
        else:
            location.geom = row['the_geom']

        if parent and parent_instance:
            logger.info("Updating parent:{} for location {}".format(parent_instance, location))
            location.parent = parent_instance

        try:
            location.save()
        except IntegrityError:
            logger.exception('Error while saving location: %s', site_name)
            return False, sites_not_added, sites_created, sites_updated

        sites_updated += 1

        logger.info('{}: {} ({})'.format(
            'Updated',
            location.name,
            carto_table.location_type.name
        ))
        return True, sites_not_added, sites_created, sites_updated


@app.task
def update_sites_from_cartodb(carto_table_pk):

    try:
        carto_table = CartoDBTable.objects.get(pk=carto_table_pk)
    except CartoDBTable.DoesNotExist:
        logger.exception('Cannot retrieve CartoDBTable with pk: %s', carto_table_pk)
        return

    auth_client = EtoolsCartoNoAuthClient(base_url="https://{}.carto.com/".format(carto_table.domain))
    sql_client = SQLClient(auth_client)
    sites_created = sites_updated = sites_not_added = 0

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
        return "Table name {}: {} sites created, {} sites updated, {} sites skipped".format(
            carto_table.table_name, 0, 0, 0
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

                    # create the actual location or retrieve existing based on type and code
                    succ, sites_not_added, sites_created, sites_updated = create_location(
                        pcode, carto_table,
                        parent, parent_instance,
                        site_name, row,
                        sites_not_added, sites_created,
                        sites_updated)

            Location.objects.rebuild()

    return "Table name {}: {} sites created, {} sites updated, {} sites skipped".format(
        carto_table.table_name, sites_created, sites_updated, sites_not_added)
