import time

from django.db import transaction
from django.utils.encoding import force_text

import celery
from carto.exceptions import CartoException
from carto.sql import SQLClient
from celery.utils.log import get_task_logger
from unicef_locations.auth import LocationsCartoNoAuthClient
from unicef_locations.models import CartoDBTable, Location

from etools.libraries.locations.task_utils import (
    cleanup_obsolete_locations,
    create_location,
    duplicate_pcodes_exist,
    filter_remapped_locations,
    get_location_ids_in_use,
    remap_location,
    save_location_remap_history,
    validate_remap_table,
)

logger = get_task_logger(__name__)


@celery.current_app.task
def validate_carto_locations_in_use(carto_table_pk):
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

        remap_table_pcode_pairs = []
        if carto_table.remap_table_name:
            remap_qry = 'select old_pcode::text, new_pcode::text from {}'.format(carto_table.remap_table_name)
            remap_table_pcode_pairs = sql_client.send(remap_qry)['rows']

    except CartoException as e:
        logger.exception("CartoDB exception occured during the data validation.")
        raise e

    remap_old_pcodes = [remap_row['old_pcode'] for remap_row in remap_table_pcode_pairs]
    orphaned_pcodes = set(database_pcodes) - (set(new_carto_pcodes) | set(remap_old_pcodes))
    orphaned_location_ids = Location.objects.all_locations().filter(p_code__in=list(orphaned_pcodes))

    # if location ids with no remap in use are found, do not continue the import
    location_ids_bnriu = get_location_ids_in_use(orphaned_location_ids)
    if location_ids_bnriu:
        msg = "Location ids in use without remap found: {}". format(','.join([str(iu) for iu in location_ids_bnriu]))
        logger.exception(msg)
        raise NoRemapInUseException(msg)

    return True


@celery.current_app.task # noqa: ignore=C901
def update_sites_from_cartodb(carto_table_pk):
    results = []

    try:
        carto_table = CartoDBTable.objects.get(pk=carto_table_pk)
    except CartoDBTable.DoesNotExist:
        logger.exception('Cannot retrieve CartoDBTable with pk: %s', carto_table_pk)
        return results

    auth_client = LocationsCartoNoAuthClient(base_url="https://{}.carto.com/".format(carto_table.domain))
    sql_client = SQLClient(auth_client)
    sites_created = sites_updated = sites_remapped = sites_not_added = 0

    try:
        # query cartodb for the locations with geometries
        carto_succesfully_queried, rows = get_cartodb_locations(sql_client, carto_table)

        if not carto_succesfully_queried:
            return results
    except CartoException:  # pragma: no-cover
        logger.exception("CartoDB exception occured")
    else:
        # validations
        # get the list of the existing Pcodes and previous Pcodes from the database
        database_pcodes = []
        for row in Location.objects.all_locations().filter(gateway=carto_table.location_type).values('p_code'):
            database_pcodes.append(row['p_code'])

        # get the list of the new Pcodes from the Carto data
        new_carto_pcodes = [str(row[carto_table.pcode_col]) for row in rows]
        remapped_old_pcodes = []

        if carto_table.remap_table_name:
            try:
                remap_qry = 'select old_pcode::text, new_pcode::text from {}'.format(
                    carto_table.remap_table_name)
                remapped_pcode_pairs = sql_client.send(remap_qry)['rows']
                # validate remap table contents
                remap_table_valid, remapped_old_pcodes, remap_new_pcodes = \
                    validate_remap_table(remapped_pcode_pairs, database_pcodes, new_carto_pcodes)

                if not remap_table_valid:
                    return results
            except CartoException:  # pragma: no-cover
                logger.exception("Cannot fetch location remap table from CartoDB")
                return results

        # check for  duplicate pcodes in both local and Carto data
        if duplicate_pcodes_exist(database_pcodes, new_carto_pcodes, remapped_old_pcodes):
            return results

        # wrap Location tree updates in a transaction, to prevent an invalid tree state due to errors
        with transaction.atomic():
            # should write lock the locations table until the tree is rebuilt
            Location.objects.all_locations().select_for_update().only('id')

            # disable tree 'generation' during single row updates, rebuild the tree after the rows are updated.
            with Location.objects.disable_mptt_updates():
                # update locations in two steps: first remap, then update the data. The reason of this approach is that
                # a remapped 'old' pcode can appear as a newly inserted pcode. Remapping before updating/inserting
                # should prevent the problem of archiving locations when remapping and updating at the same time.

                # REMAP locations
                if carto_table.remap_table_name and len(remapped_pcode_pairs) > 0:
                    # remapped_pcode_pairs ex.: {'old_pcode': 'ET0721', 'new_pcode': 'ET0714'}
                    remapped_pcode_pairs = list(filter(
                        filter_remapped_locations,
                        remapped_pcode_pairs
                    ))

                    aggregated_remapped_pcode_pairs = {}
                    for row in rows:
                        carto_pcode = str(row[carto_table.pcode_col]).strip()
                        for remap_row in remapped_pcode_pairs:
                            # create the location or update the existing based on type and code
                            if carto_pcode == remap_row['new_pcode']:
                                if carto_pcode not in aggregated_remapped_pcode_pairs:
                                    aggregated_remapped_pcode_pairs[carto_pcode] = []
                                aggregated_remapped_pcode_pairs[carto_pcode].append(remap_row['old_pcode'])

                    # aggregated_remapped_pcode_pairs - {'new_pcode': ['old_pcode_1', old_pcode_2, ...], ...}
                    for remapped_new_pcode, remapped_old_pcodes in aggregated_remapped_pcode_pairs.items():
                        remapped_location_id_pairs = remap_location(
                            carto_table,
                            remapped_new_pcode,
                            remapped_old_pcodes
                        )
                        # crete remap history, and remap relevant models to the new location
                        if remapped_location_id_pairs:
                            save_location_remap_history(remapped_location_id_pairs)
                            sites_remapped += 1

                # UPDATE locations
                for row in rows:
                    carto_pcode = str(row[carto_table.pcode_col]).strip()
                    site_name = row[carto_table.name_col]

                    if not site_name or site_name.isspace():
                        logger.warning("No name for location with PCode: {}".format(carto_pcode))
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

                    if not row['the_geom']:
                        sites_not_added += 1
                        continue

                    # create the location or update the existing based on type and code
                    success, sites_not_added, sites_created, sites_updated = create_location(
                        carto_pcode, carto_table,
                        parent, parent_instance,
                        site_name, row['the_geom'],
                        sites_not_added, sites_created, sites_updated
                    )
                    if success:
                        logger.warning("Location level {} imported with success".format(carto_table.location_type))

                orphaned_old_pcodes = set(database_pcodes) - (set(new_carto_pcodes) | set(remapped_old_pcodes))
                if orphaned_old_pcodes:  # pragma: no-cover
                    logger.warning("Archiving unused pcodes: {}".format(','.join(orphaned_old_pcodes)))
                    Location.objects.filter(
                        p_code__in=list(orphaned_old_pcodes),
                        is_active=True,
                    ).update(
                        is_active=False
                    )

            # rebuild location tree
            Location.objects.rebuild()

    logger.warning("Table name {}: {} sites created, {} sites updated, {} sites remapped, {} sites skipped".format(
        carto_table.table_name, sites_created, sites_updated, sites_remapped, sites_not_added))


@celery.current_app.task
def cleanup_carto_obsolete_locations(carto_table_pk):

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

        remap_table_pcode_pairs = []
        if carto_table.remap_table_name:
            remap_qry = 'select old_pcode::text, new_pcode::text from {}'.format(carto_table.remap_table_name)
            remap_table_pcode_pairs = sql_client.send(remap_qry)['rows']

    except CartoException as e:
        logger.exception("CartoDB exception occured during the data validation.")
        raise e

    remapped_pcodes = [remap_row['old_pcode'] for remap_row in remap_table_pcode_pairs]
    remapped_pcodes += [remap_row['new_pcode'] for remap_row in remap_table_pcode_pairs]
    # select for deletion those pcodes which are not present in the Carto datasets in any form
    deleteable_pcodes = set(database_pcodes) - (set(new_carto_pcodes) | set(remapped_pcodes))

    cleanup_obsolete_locations(deleteable_pcodes)


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


class NoRemapInUseException(Exception):
    pass
