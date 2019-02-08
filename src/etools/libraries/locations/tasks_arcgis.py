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
from etools.libraries.locations.task_utils import (
    get_location_ids_in_use,
    save_location_remap_history,
    validate_remap_table,
    duplicate_pcodes_exist,
    create_location,
)


logger = get_task_logger(__name__)


@celery.current_app.task
def validate_arcgis_locations_in_use(arcgis_table_pk):
    try:
        carto_table = ArcgisDBTable.objects.get(pk=arcgis_table_pk)
    except ArcgisDBTable.DoesNotExist as e:
        logger.exception('Cannot retrieve ArcgisDBTable with pk: %s', arcgis_table_pk)
        raise e

    database_pcodes = []
    for row in Location.objects.all_locations().filter(gateway=carto_table.location_type).values('p_code'):
        database_pcodes.append(row['p_code'])

    auth_client = LocationsCartoNoAuthClient(base_url="https://{}.carto.com/".format(carto_table.domain))
    sql_client = SQLClient(auth_client)

    try:
        qry = sql_client.send('select array_agg({}) AS aggregated_pcodes from {}'.format(
            carto_table.pcode_col,
            carto_table.table_name,
        ))
        new_carto_pcodes = qry['rows'][0]['aggregated_pcodes'] \
            if len(qry['rows']) > 0 and "aggregated_pcodes" in qry['rows'][0] else []

        remapped_pcode_pairs = []
        if carto_table.remap_table_name:
            remap_qry = 'select old_pcode::text, new_pcode::text from {}'.format(carto_table.remap_table_name)
            remapped_pcode_pairs = sql_client.send(remap_qry)['rows']

    except RuntimeError as e:
        logger.exception("Cannot fetch location data from Arcgis")
        raise e

    remapped_old_pcodes = [remap_row['old_pcode'] for remap_row in remapped_pcode_pairs]
    orphaned_pcodes = set(database_pcodes) - (set(new_carto_pcodes) | set(remapped_old_pcodes))
    orphaned_location_ids = Location.objects.all_locations().filter(p_code__in=list(orphaned_pcodes))

    # if location ids with no remap in use are found, do not continue the import
    location_ids_bnriu = get_location_ids_in_use(orphaned_location_ids)
    if location_ids_bnriu:
        msg = "Location ids in use without remap found: {}". format(','.join([str(iu) for iu in location_ids_bnriu]))
        logger.exception(msg)
        raise NoRemapInUseException(msg)

    return True


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

    remapped_old_pcodes = []
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
            remap_table_valid, remapped_old_pcodes, remap_new_pcodes = \
                validate_remap_table(remapped_pcode_pairs, database_pcodes, arcgis_pcodes)

            if not remap_table_valid:
                return results
        except RuntimeError:  # pragma: no-cover
            logger.exception("Cannot fetch location remap data from Arcgis")
            return results

    # check for  duplicate pcodes in both local and new data
    if duplicate_pcodes_exist(database_pcodes, arcgis_pcodes, remapped_old_pcodes):
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

            orphaned_old_pcodes = set(database_pcodes) - (set(arcgis_pcodes) | set(remapped_old_pcodes))
            if orphaned_old_pcodes:  # pragma: no-cover
                logger.warning("Archiving unused pcodes: {}".format(','.join(orphaned_old_pcodes)))
                Location.objects.filter(p_code__in=list(orphaned_old_pcodes)).update(is_active=False)

        Location.objects.rebuild()

    logger.warning("Table name {}: {} sites created, {} sites updated, {} sites remapped, {} sites skipped".format(
        arcgis_table.service_name, sites_created, sites_updated, sites_remapped, sites_not_added))

    return results


@celery.current_app.task
def cleanup_arcgis_obsolete_locations(arcgis_table_pk):
    try:
        carto_table = CartoDBTable.objects.get(pk=carto_table_pk)
    except CartoDBTable.DoesNotExist as e:
        logger.exception('Cannot retrieve CartoDBTable with pk: %s', carto_table_pk)
        raise e

    database_pcodes = []
    for row in Location.objects.all_locations().filter(gateway=carto_table.location_type).values('p_code'):
        database_pcodes.append(row['p_code'])

    auth_client = LocationsCartoNoAuthClient(base_url="https://{}.carto.com/".format(carto_table.domain))
    sql_client = SQLClient(auth_client)

    try:
        qry = sql_client.send('select array_agg({}) AS aggregated_pcodes from {}'.format(
            carto_table.pcode_col,
            carto_table.table_name,
        ))
        new_carto_pcodes = qry['rows'][0]['aggregated_pcodes'] \
            if len(qry['rows']) > 0 and "aggregated_pcodes" in qry['rows'][0] else []

        remapped_pcode_pairs = []
        if carto_table.remap_table_name:
            remap_qry = 'select old_pcode::text, new_pcode::text from {}'.format(carto_table.remap_table_name)
            remapped_pcode_pairs = sql_client.send(remap_qry)['rows']

    except CartoException as e:
        logger.exception("CartoDB exception occured during the data validation.")
        raise e

    remapped_pcodes = [remap_row['old_pcode'] for remap_row in remapped_pcode_pairs]
    remapped_pcodes += [remap_row['new_pcode'] for remap_row in remapped_pcode_pairs]
    # select for deletion those pcodes which are not present in the Carto datasets in any form
    deleteable_pcodes = set(database_pcodes) - (set(new_carto_pcodes) | set(remapped_pcodes))

    # Do a few safety checks before we actually delete a location, like:
    # - ensure that the deleted locations doesn't have any children in the location tree
    # - check if the deleted location was remapped before, do not delete if yes.
    # if the checks pass, add the deleteable location ID to the `revalidated_deleteable_pcodes` array so they can be
    # deleted in one go later
    revalidated_deleteable_pcodes = []

    with transaction.atomic():
        # prevent writing into locations until the cleanup is done
        Location.objects.all_locations().select_for_update().only('id')

        for deleteable_pcode in deleteable_pcodes:
            try:
                deleteable_location = Location.objects.all_locations().get(p_code=deleteable_pcode)
            except Location.DoesNotExist:
                logger.warning("Cannot find orphaned pcode {}.".format(deleteable_pcode))
            else:
                if deleteable_location.is_leaf_node():
                    secondary_parent_check = Location.objects.all_locations().filter(
                        parent=deleteable_location.id
                    ).exists()
                    remap_history_check = LocationRemapHistory.objects.filter(
                        Q(old_location=deleteable_location) | Q(new_location=deleteable_location)
                    ).exists()
                    if not secondary_parent_check and not remap_history_check:
                        logger.info("Selecting orphaned pcode {} for deletion".format(deleteable_location.p_code))
                        revalidated_deleteable_pcodes.append(deleteable_location.id)

        # delete the selected locations all at once, it seems it's faster like this compared to deleting them one by one.
        if revalidated_deleteable_pcodes:
            logger.info("Deleting selected orphaned pcodes")
            Location.objects.all_locations().filter(id__in=revalidated_deleteable_pcodes).delete()

        # rebuild location tree after the unneeded locations are cleaned up, because it seems deleting locations
        # sometimes leaves the location tree in a `bugged` state
        Location.objects.rebuild()


class NoRemapInUseException(Exception):
    pass
