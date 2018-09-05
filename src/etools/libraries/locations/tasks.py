import celery
from carto.exceptions import CartoException
from carto.sql import SQLClient
from celery.utils.log import get_task_logger

from django.contrib.contenttypes.models import ContentType
# from django.db import IntegrityError, transaction
# from django.utils.encoding import force_text

from unicef_locations.models import CartoDBTable, Location, LocationRemapHistory
# from unicef_locations.tasks import update_sites_from_cartodb

from etools.applications.partners.models import Intervention
from etools.applications.reports.models import AppliedIndicator
from etools.applications.t2f.models import TravelActivity
from etools.applications.activities.models import Activity
from etools.applications.action_points.models import ActionPoint


logger = get_task_logger(__name__)

@celery.current_app.task
def save_location_remap_history(imported_locations):
    '''
    :param imported_locations: set of (new_location, remapped_location) tuples
    :return:
    '''

    if not imported_locations:
        return

    remapped_locations = {loc[1]:loc[0] for loc in imported_locations if loc[1]}

    if not remapped_locations:
        return

    # remap related entities to the newly added locations, and save the location remap history
    # interventions
    ctp = ContentType.objects.get(app_label='partners', model='intervention')
    '''
    for intervention in Intervention.objects.filter(flat_locations__in=list(remapped_locations.keys())).distinct():
        print("-------------------")
        print(intervention.id)
        print(",".join([str(ix.id) for ix in intervention.flat_locations.all()]))
        return
    '''

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
        actionpoint.location.id=new_location
        actionpoint.save()
        # TODO: logs
