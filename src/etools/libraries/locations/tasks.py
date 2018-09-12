import celery
from carto.exceptions import CartoException
from carto.sql import SQLClient
from celery.utils.log import get_task_logger

from django.contrib.contenttypes.models import ContentType

from unicef_locations.models import CartoDBTable, Location, LocationRemapHistory
from unicef_locations.auth import LocationsCartoNoAuthClient

from etools.applications.partners.models import Intervention
from etools.applications.reports.models import AppliedIndicator
from etools.applications.t2f.models import TravelActivity
from etools.applications.activities.models import Activity
from etools.applications.action_points.models import ActionPoint


logger = get_task_logger(__name__)


@celery.current_app.task(bind=True)
def validate_locations_in_use(self, carto_table_pk):
    try:
        carto_table = CartoDBTable.objects.get(pk=carto_table_pk)
    except CartoDBTable.DoesNotExist as e:
        logger.exception('Cannot retrieve CartoDBTable with pk: %s', carto_table_pk)
        raise e

    database_pcodes = []
    for row in Location.all_locations.filter(gateway=carto_table.location_type).values('p_code'):
        database_pcodes.append(row['p_code'])

    auth_client = LocationsCartoNoAuthClient(base_url="https://{}.carto.com/".format(carto_table.domain))
    sql_client = SQLClient(auth_client)

    try:
        qry = sql_client.send('select array_agg({}) AS aggregated_pcodes from {}'.format(
            carto_table.pcode_col,
            carto_table.table_name,
        ))
        new_carto_pcodes = qry['rows'][0]['aggregated_pcodes']

        remapped_pcode_pairs = []
        if carto_table.remap_table_name:
            remap_qry = 'select old_pcode::text, new_pcode::text from {}'.format(carto_table.remap_table_name)
            remapped_pcode_pairs = sql_client.send(remap_qry)['rows']

    except CartoException as e:
        logger.exception("CartoDB exception occured during the data validation.")
        raise e

    remap_old_pcodes = [remap_row['old_pcode'] for remap_row in remapped_pcode_pairs]
    orphaned_pcodes = set(database_pcodes) - (set(new_carto_pcodes) | set(remap_old_pcodes))
    orphaned_location_ids = Location.all_locations.filter(p_code__in=list(orphaned_pcodes))

    # location ids with no remap but in use
    location_ids_bnriu = get_location_ids_in_use(orphaned_location_ids)
    if location_ids_bnriu:
        msg = "Location ids in use without remap found: {}". format(','.join([str(iu) for iu in location_ids_bnriu]))
        logger.exception(msg)
        # why this does not work..
        # self.request.callbacks = self.request.chain = None
        raise Exception(msg)

    return True


@celery.current_app.task(bind=True)
def save_location_remap_history(self, imported_locations):
    '''
    :param imported_locations: set of (new_location, remapped_location) tuples
    :return:
    '''

    if not imported_locations:
        return

    remapped_locations = {loc[1]: loc[0] for loc in imported_locations if loc[1]}

    if not remapped_locations:
        return

    # remap related entities to the newly added locations, and save the location remap history
    # interventions
    ctp = ContentType.objects.get(app_label='partners', model='intervention')
    for intervention in Intervention.objects.filter(flat_locations__in=remapped_locations.keys()).distinct():
        for remapped_location in intervention.flat_locations.filter(id__in=list(remapped_locations.keys())):
            new_location = remapped_locations.get(remapped_location.id)
            LocationRemapHistory.objects.create(
                old_location=remapped_location,
                new_location=new_location,
                content_type=ctp,
                object_id=intervention.id,
            )
            intervention.flat_locations.remove(remapped_location)
            intervention.flat_locations.add(new_location)
            # TODO: logs

    # intervention indicators
    ctp = ContentType.objects.get(app_label='reports', model='appliedindicator')
    for appliedindicator in AppliedIndicator.objects.filter(locations__in=list(remapped_locations.keys())).distinct():
        for remapped_location in appliedindicator.locations.filter(id__in=list(remapped_locations.keys())):
            new_location = remapped_locations.get(remapped_location.id)
            LocationRemapHistory.objects.create(
                old_location=remapped_location,
                new_location=new_location,
                content_type=ctp,
                object_id=appliedindicator.id,
            )
            appliedindicator.locations.remove(remapped_location)
            appliedindicator.locations.add(new_location)
            # TODO: logs

    # travel activities
    ctp = ContentType.objects.get(app_label='t2f', model='travelactivity')
    for travelactivity in TravelActivity.objects.filter(locations__in=list(remapped_locations.keys())).distinct():
        for remapped_location in travelactivity.locations.filter(id__in=list(remapped_locations.keys())):
            new_location = remapped_locations.get(remapped_location.id)
            LocationRemapHistory.objects.create(
                old_location=remapped_location,
                new_location=new_location,
                content_type=ctp,
                object_id=travelactivity.id,
            )
            travelactivity.locations.remove(remapped_location)
            travelactivity.locations.add(new_location)
            # TODO: logs

    # activities
    ctp = ContentType.objects.get(app_label='activities', model='activity')
    for activity in Activity.objects.filter(locations__in=list(remapped_locations.keys())).distinct():
        for remapped_location in activity.locations.filter(id__in=list(remapped_locations.keys())):
            new_location = remapped_locations.get(remapped_location.id)
            LocationRemapHistory.objects.create(
                old_location=remapped_location,
                new_location=new_location,
                content_type=ctp,
                object_id=activity.id,
            )
            activity.locations.remove(remapped_location)
            activity.locations.add(new_location)
            # TODO: logs

    # action points
    ctp = ContentType.objects.get(app_label='action_points', model='actionpoint')
    for actionpoint in ActionPoint.objects.filter(location__in=list(remapped_locations.keys())).distinct():
        new_location = remapped_locations.get(actionpoint.location.id)
        LocationRemapHistory.objects.create(
            old_location=actionpoint.location.id,
            new_location=new_location,
            content_type=ctp,
            object_id=actionpoint.id,
        )
        actionpoint.location.id = new_location
        actionpoint.save()
        # TODO: logs


@celery.current_app.task(bind=True)
def cleanup_obsolete_locations(self, carto_table_pk):

    try:
        carto_table = CartoDBTable.objects.get(pk=carto_table_pk)
    except CartoDBTable.DoesNotExist as e:
        logger.exception('Cannot retrieve CartoDBTable with pk: %s', carto_table_pk)
        raise e

    database_pcodes = []
    for row in Location.all_locations.filter(gateway=carto_table.location_type).values('p_code'):
        database_pcodes.append(row['p_code'])

    auth_client = LocationsCartoNoAuthClient(base_url="https://{}.carto.com/".format(carto_table.domain))
    sql_client = SQLClient(auth_client)

    try:
        qry = sql_client.send('select array_agg({}) AS aggregated_pcodes from {}'.format(
            carto_table.pcode_col,
            carto_table.table_name,
        ))
        new_carto_pcodes = qry['rows'][0]['aggregated_pcodes']

        remapped_pcode_pairs = []
        if carto_table.remap_table_name:
            remap_qry = 'select old_pcode::text, new_pcode::text from {}'.format(carto_table.remap_table_name)
            remapped_pcode_pairs = sql_client.send(remap_qry)['rows']

    except CartoException as e:
        logger.exception("CartoDB exception occured during the data validation.")
        raise e

    remapped_pcodes = [remap_row['old_pcode'] for remap_row in remapped_pcode_pairs]
    remapped_pcodes += [remap_row['new_pcode'] for remap_row in remapped_pcode_pairs]
    deleteable_pcodes = set(database_pcodes) - (set(new_carto_pcodes) | set(remapped_pcodes))

    for deleteable_pcode in deleteable_pcodes:
        try:
            deleteable_location = Location.all_locations.get(p_code=deleteable_pcode)
        except Location.DoesNotExist:
            logger.warning("Cannot find orphaned pcode {}.".format(deleteable_pcode))
        else:
            if deleteable_location.is_leaf_node():
                logger.info("Deleting orphaned and unused location with pcode {}".format(deleteable_location.p_code))
                deleteable_location.delete()


@celery.current_app.task
def catch_task_errors():
    pass


def get_location_ids_in_use(location_ids):
    """
    :param location_ids:
    :return location_ids_in_use:
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


class BnriuException(Exception):
    pass
