import time

from carto.exceptions import CartoException
from celery.utils.log import get_task_logger
from unicef_locations.models import Location

from etools.libraries.locations.exceptions import InvalidRemap

logger = get_task_logger(__name__)


def get_remapping(sql_client, carto_table):
    remap_dict = dict()
    to_deactivate = list()
    if carto_table.remap_table_name:
        try:
            remap_qry = f'select old_pcode::text, new_pcode::text, matching::int from {carto_table.remap_table_name}'
            remap_table = sql_client.send(remap_qry)['rows']
        except CartoException as e:
            logger.exception(str(e))
            raise CartoException
        for remap_row in remap_table:
            old, new, matching = remap_row['old_pcode'], remap_row['new_pcode'], remap_row['matching']
            if matching:
                if old in remap_dict:
                    raise InvalidRemap
                remap_dict[old] = new
            else:
                to_deactivate.append(old)

    temp = 0
    acyclic_dict = dict()
    adjusters = dict()
    for key, value in remap_dict.items():
        if key in remap_dict.values() and key != value:
            acyclic_dict[key] = f'temp{temp}'
            adjusters[f'temp{temp}'] = value
            temp += 1
        else:
            acyclic_dict[key] = value
    for key, value in adjusters.items():
        acyclic_dict[key] = value
    return acyclic_dict, to_deactivate


def create_or_update_locations(rows, carto_table):

    new, updated, skipped, error = 0, 0, 0, 0

    for row in rows:
        pcode = row[carto_table.pcode_col]
        name = row[carto_table.name_col]
        geom = row['the_geom']

        if all([name, pcode, geom]):
            geom_key = 'point' if 'Point' in row['the_geom'] else 'geom'
            default_dict = {
                'gateway': carto_table.location_type,
                'name': name,
                geom_key: geom,
            }

            parent_pcode = row[carto_table.parent_code_col] if carto_table.parent_code_col in row else None
            if parent_pcode:
                try:
                    parent = Location.objects.get(p_code=parent_pcode, is_active=True)
                    default_dict['parent'] = parent
                except (Location.DoesNotExist, Location.MultipleObjectsReturned):
                    skipped += 1
                    logger.info(f"Skipping row pcode {pcode}")
                    continue

            try:
                location, created = Location.objects.get_or_create(p_code=pcode, is_active=True, defaults=default_dict)
                if created:
                    new += 1
                else:
                    for attr, value in default_dict.items():
                        setattr(location, attr, value)
                    location.save()
                    updated += 1

            except Location.MultipleObjectsReturned:
                logger.warning(f"Multiple locations found for: {carto_table.location_type}, {name} ({pcode})")
                error += 1

        else:
            skipped += 1
            logger.info(f"Skipping row pcode {pcode}")

    return new, updated, skipped, error


def get_cartodb_locations(sql_client, carto_table, cartodb_id_col='cartodb_id'):
    """
    returns locations referenced by cartodb_table
    """
    rows = []
    try:
        row_count = sql_client.send(f'select count(*) from {carto_table.table_name}')['rows'][0]['count']
        max_id = sql_client.send(f'select MAX({cartodb_id_col}) from {carto_table.table_name}')['rows'][0]['max']
    except CartoException:  # pragma: no-cover
        logger.exception(f"Cannot fetch pagination prequisites from CartoDB for table {carto_table.table_name}")
        raise CartoException

    offset, limit = 0, 100

    if max_id > (5 * row_count):  # failsafe in the case when cartodb id's are too much off compared to the nr. of records
        limit = max_id + 1
        logger.warning("The CartoDB primary key seems off, pagination is not possible")

    parent_qry = f', {carto_table.parent_code_col}' if carto_table.parent_code_col and carto_table.parent else ''
    base_qry = f'select st_AsGeoJSON(the_geom) as the_geom, {carto_table.name_col}, {carto_table.pcode_col}{parent_qry} ' \
               f'from {carto_table.table_name}'

    while offset <= max_id:
        logger.info(f'Requesting rows between {offset} and {offset + limit} for {carto_table.table_name}')
        paged_qry = base_qry + f' WHERE {cartodb_id_col} > {offset} AND {cartodb_id_col} <= {offset + limit}'
        time.sleep(0.1)  # do not spam Carto with requests
        new_rows = query_with_retries(sql_client, paged_qry, offset)
        rows += new_rows
        offset += limit

    return rows


def query_with_retries(sql_client, query, offset, max_retries=5):
    """
    Query CartoDB with retries
    """

    retries = 0
    while retries < max_retries:
        time.sleep(0.1)
        retries += 1
        try:
            sites = sql_client.send(query)
        except CartoException:
            if retries < max_retries:
                logger.warning('Retrying again table page at offset {}'.format(offset))

        if 'error' in sites:
            raise CartoException
        return sites['rows']
    raise CartoException
