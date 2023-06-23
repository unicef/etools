import logging
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db.models.deletion import Collector, ProtectedError

import celery
from carto.exceptions import CartoException
from celery.utils.log import get_task_logger
from tenant_schemas_celery.app import get_schema_name_from_task
from unicef_locations.models import CartoDBTable
from unicef_locations.synchronizers import LocationSynchronizer
from unicef_locations.utils import get_location_model
from unicef_vision.utils import get_vision_logger_domain_model

from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.users.models import Country

logger = get_task_logger(__name__)


class eToolsLocationSynchronizer(LocationSynchronizer):
    """eTools version of synchronizer with use the VisionSyncLog to store log execution"""

    def __init__(self, pk, schema) -> None:
        super().__init__(pk)
        country = Country.objects.get(schema_name=schema)
        self.log, _ = get_vision_logger_domain_model().objects.get_or_create(
            handler_name=f'LocationsHandler (lev{self.carto.admin_level})',
            business_area_code=getattr(country, 'business_area_code', ''),
            country=country,
            details=self.__class__.__name__
        )

    def sync(self):
        try:
            new, updated, skipped, error = super().sync()
            self.log.total_records = new + updated + skipped + error
            self.log.total_processed = new + updated
            self.log.successful = True
            self.log.exception_message = 'Congrats: Success'
        except CartoException as e:
            self.log.exception_message = e
            self.log.successful = False
        finally:
            self.log.save()

    def post_sync(self):
        # update sites
        for site in LocationSite.objects.all():
            parent = site.get_parent_location()
            if site.parent != parent:
                site.parent = parent
                site.save()

        # update monitoring activities
        for activity in MonitoringActivity.objects.filter(location_site__isnull=False):
            if activity.site.parent != activity.location:
                activity.location = activity.site.parent
                activity.save()

    def handle_obsolete_locations(self, to_deactivate):
        """
        Handle obsolate locations:
        - deactivate referenced locations
        - delete non referenced locations
        """
        logging.info('Clean Obsolate Locations')
        for location in get_location_model().objects.filter(p_code__in=to_deactivate):
            collector = Collector(using='default')
            protected = False
            try:
                collector.collect([location])
            except ProtectedError:
                protected = True
            if protected or collector.dependencies or location.get_children():
                location.name = f"{location.name} [{datetime.today().strftime('%Y-%m-%d')}]"
                location.is_active = False
                location.save()
                logger.info(f'Deactivating {location}')
            else:
                location.delete()
                logger.info(f'Deleting {location}')


@celery.current_app.task(bind=True)
def import_locations(self, carto_table_pk):
    """
    Delete all locations that are not matching* in the remap table and are not in use (referenced models).
    Deactivate all locations that are in use and are not matching* in the remap table.

    In use no Matching no => Delete
    In use yes Matching no => Deactivate
    In use yes/no Matching yes => Update

    Iterate on all the “new” locations:
    if they have match update else create
    """

    schema = get_schema_name_from_task(self, dict)
    eToolsLocationSynchronizer(carto_table_pk, schema).sync()


@celery.current_app.task
def notify_import_site_completed(carto_table_pk, user_pk):
    user = get_user_model().objects.get(pk=user_pk)
    context = {
        'table': CartoDBTable.objects.get(pk=carto_table_pk),
        'recipient': user.get_full_name(),
    }
    send_notification_with_template(
        recipients=[user.email],
        template_name='locations/import_completed',
        context=context
    )
