from django.db import IntegrityError

from carto.auth import APIKeyAuthClient
from carto.exceptions import CartoException
from carto.sql import SQLClient
from celery.utils.log import get_task_logger

from EquiTrack.celery import app
from locations.models import CartoDBTable, Location

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
        except IntegrityError as e:
            logger.info('Not Added: {}', e)

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

        try:
            location.save()
        except IntegrityError as e:
            logger.exception('Error whilst saving location: {}'.format(site_name))
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
        logger.exception('Cannot retrieve CartoDBTable with pk: {}'.format(carto_table_pk))
        return

    auth_client = APIKeyAuthClient(api_key=carto_table.api_key,
                                   base_url="https://{}.carto.com/".format(carto_table.domain))
    sql_client = SQLClient(auth_client)
    sites_created = sites_updated = sites_not_added = 0
    try:
        # query for cartodb
        qry = ''
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

        sites = sql_client.send(qry)
    except CartoException as exc:
        logger.exception("CartoDB exception occured {}".format(exc))
    else:

        for row in sites['rows']:
            pcode = str(row[carto_table.pcode_col]).strip()
            site_name = row[carto_table.name_col]

            if not site_name or site_name.isspace():
                logger.warning("No name for location with PCode: {}".format(pcode))
                sites_not_added += 1
                continue

            site_name = site_name.encode('UTF-8')

            parent = None
            parent_code = None
            parent_instance = None

            # attempt to reference the parent of this location
            if carto_table.parent_code_col and carto_table.parent:
                try:
                    parent = carto_table.parent.__class__
                    parent_code = row[carto_table.parent_code_col]
                    parent_instance = Location.objects.get(p_code=parent_code)
                except Exception as exp:
                    msg = " "
                    if exp is parent.MultipleObjectsReturned:
                        msg = "{} locations found for parent code: {}".format(
                            'Multiple' if exp is parent.MultipleObjectsReturned else 'No',
                            parent_code
                        )
                    else:
                        msg = exp.message
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

    return "Table name {}: {} sites created, {} sites updated, {} sites skipped".format(
        carto_table.table_name, sites_created, sites_updated, sites_not_added)
