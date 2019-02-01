import json
import time

import celery
from celery.utils.log import get_task_logger
from arcgis.features import FeatureCollection, Feature, FeatureLayer, FeatureSet
from django.db import IntegrityError, transaction
from django.utils.encoding import force_text
from django.contrib.gis.geos import Polygon, MultiPolygon, Point

from unicef_locations.models import ArcgisDBTable, Location
from .task_utils import create_location, validate_remap_table, duplicate_pcodes_exist

logger = get_task_logger(__name__)

@celery.current_app.task # noqa: ignore=C901
def import_arcgis_locations(arcgis_table_pk):
    results = []
    sites_created = sites_updated = sites_remapped = sites_not_added = 0

    try:
        arcgis_table = ArcgisDBTable.objects.get(pk=arcgis_table_pk)
    except ArcgisDBTable.DoesNotExist:
        logger.exception('Cannot retrieve ArcgisDBTable with pk: %s', arcgis_table_pk)
        return results

    database_pcodes = []
    for row in Location.objects.all_locations().filter(gateway=arcgis_table.location_type).values('p_code'):
        database_pcodes.append(row['p_code'])

    # https://esri.github.io/arcgis-python-api/apidoc/html/arcgis.features.toc.html#
    try:
        feature_layer = FeatureLayer(arcgis_table.service_url)
        featurecollection = json.loads(feature_layer.query(out_sr=4326).to_geojson)
        rows = featurecollection['features']
    except RuntimeError:  # pragma: no-cover
        logger.exception("Cannot fetch location data from Arcgis")
        return results

    arcgis_pcodes = [str(row['properties'][arcgis_table.pcode_col].strip()) for row in rows]

    remap_old_pcodes = []
    if arcgis_table.remap_table_service_url:
        try:
            remapped_pcode_pairs = []
            remap_feature_layer = FeatureLayer(arcgis_table.remap_table_service_url)
            remap_rows = remap_feature_layer.query()

            for row in remap_rows:
                remapped_pcode_pairs.append({
                    "old_pcode": row.get_value("old_pcode"),
                    "new_pcode": row.get_value("new_pcode"),
                })

            # validate remap table contents
            remap_table_valid, remap_old_pcodes, remap_new_pcodes = \
                validate_remap_table(remapped_pcode_pairs, database_pcodes, arcgis_pcodes)

            if not remap_table_valid:
                return results
        except RuntimeError:  # pragma: no-cover
            logger.exception("Cannot fetch location remap data from Arcgis")
            return results

    # check for  duplicate pcodes in both local and new data
    if duplicate_pcodes_exist(database_pcodes, arcgis_pcodes, remap_old_pcodes):
        return results

    with transaction.atomic():
        # we should write lock the locations table until the location tree is rebuilt
        Location.objects.all_locations().select_for_update().only('id')

        with Location.objects.disable_mptt_updates():
            for row in rows:
                arcgis_pcode = str(row['properties'][arcgis_table.pcode_col]).strip()
                site_name = row['properties'][arcgis_table.name_col]

                if not site_name or site_name.isspace():
                    logger.warning("No name for location with PCode: {}".format(arcgis_pcode))
                    sites_not_added += 1
                    continue

                parent = None
                parent_code = None
                parent_instance = None

                if arcgis_table.parent_code_col and arcgis_table.parent:
                    msg = None
                    parent = arcgis_table.parent.__class__
                    parent_code = row['properties'][arcgis_table.parent_code_col]
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

                # check if the new location should be remapped to an old location
                remapped_old_pcodes = set()
                if arcgis_table.remap_table_service_url and len(remapped_pcode_pairs) > 0:  # pragma: no-cover
                    for remap_row in remapped_pcode_pairs:
                        if arcgis_pcode == remap_row['new_pcode']:
                            remapped_old_pcodes.add(remap_row['old_pcode'])

                if row['geometry']['type'] == 'Polygon':
                    geom = MultiPolygon([Polygon(coord) for coord in row['geometry']['coordinates']])
                elif row['geometry']['type'] == 'Point':
                    # TODO test with real data
                    geom = Point(row['geometry']['coordinates'])
                else:
                    logger.warning("Invalid Arcgis location type for: {}".format(arcgis_pcode))
                    sites_not_added += 1
                    continue

                # create the location or update the existing based on type and code
                succ, sites_not_added, sites_created, sites_updated, sites_remapped, \
                partial_results = create_location(
                    arcgis_pcode, arcgis_table.location_type,
                    parent, parent_instance, remapped_old_pcodes,
                    site_name, geom.json,
                    sites_not_added, sites_created,
                    sites_updated, sites_remapped
                )

                results += partial_results

            orphaned_old_pcodes = set(database_pcodes) - (set(arcgis_pcodes) | set(remap_old_pcodes))
            if orphaned_old_pcodes:  # pragma: no-cover
                logger.warning("Archiving unused pcodes: {}".format(','.join(orphaned_old_pcodes)))
                Location.objects.filter(p_code__in=list(orphaned_old_pcodes)).update(is_active=False)

        Location.objects.rebuild()

    logger.warning("Table name {}: {} sites created, {} sites updated, {} sites remapped, {} sites skipped".format(
        arcgis_table.service_name, sites_created, sites_updated, sites_remapped, sites_not_added))

    return results