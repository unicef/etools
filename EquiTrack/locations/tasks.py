import logging
from django.db import IntegrityError
from cartodb import CartoDBAPIKey, CartoDBException

from EquiTrack.celery import app
from .models import Location

logger = logging.getLogger('locations.models')


@app.task
def update_sites_from_cartodb(carto_table):

    client = CartoDBAPIKey(carto_table.api_key, carto_table.domain)

    sites_created = sites_updated = sites_not_added = 0
    try:
        sites = client.sql(
            'select * from {}'.format(carto_table.table_name)
        )
    except CartoDBException as e:
        logging.exception("CartoDB exception occured", exc_info=True)
    else:

        for row in sites['rows']:
            pcode = str(row[carto_table.pcode_col]).strip()
            site_name = row[carto_table.name_col].encode('UTF-8')

            if not site_name or site_name.isspace():
                logger.warning("No name for location with PCode: {}".format(pcode))
                sites_not_added += 1
                continue

            parent = None
            parent_code = None
            parent_instance = None

            # attempt to reference the parent of this location
            if carto_table.parent_code_col and carto_table.parent:
                try:
                    parent = carto_table.parent.__class__
                    parent_code = row[carto_table.parent_code_col]
                    parent_instance = Location.objects.get(p_code=parent_code)
                except (parent.DoesNotExist, parent.MultipleObjectsReturned) as exp:
                    msg = "{} locations found for parent code: {}".format(
                        'Multiple' if exp is parent.MultipleObjectsReturned else 'No',
                        parent_code
                    )
                    logger.warning(msg)
                    sites_not_added += 1
                    continue

            # create the actual location or retrieve existing based on type and code
            try:
                create_args = {
                    'p_code': pcode,
                    'gateway': carto_table.location_type
                }
                if parent and parent_instance:
                    create_args['parent'] = parent_instance
                location, created = Location.objects.get_or_create(**create_args)
            except Location.MultipleObjectsReturned:
                logger.warning("Multiple locations found for: {}, {} ({})".format(
                    carto_table.location_type, site_name, pcode
                ))
                sites_not_added += 1
                continue
            else:
                if created:
                    sites_created += 1
                else:
                    sites_updated += 1

                # names can be updated for existing locations with the same code
                location.name = site_name

                # figure out its geographic type
                #TODO: a bit rudimentary, could be more robust
                if 'Point' in row['the_geom']:
                    location.point = row['the_geom']
                else:
                    location.geom = row['the_geom']

                try:
                    location.save()
                except IntegrityError as e:
                    logger.exception('Error whilst saving location: {}'.format(site_name))
                    sites_not_added += 1
                    continue

            logger.info('{}: {} ({})'.format(
                'Added' if created else 'Updated',
                location.name,
                carto_table.location_type.name
            ))

    return "Table name {}: {} sites created, {} sites updated, {} sites skipped".format(
                carto_table.table_name, sites_created, sites_updated, sites_not_added
            )
