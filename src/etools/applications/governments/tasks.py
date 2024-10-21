import datetime

from django.conf import settings
from django.db import connection
from django.utils import timezone

from celery.utils.log import get_task_logger
from django_tenants.utils import get_tenant_model, schema_context

from etools.applications.governments.models import GDD, GDDActivity
from etools.applications.governments.serializers.exports.vision.gdd_v1 import GDDVisionExportSerializer
from etools.applications.partners.synchronizers import VisionUploader
from etools.config.celery import app

logger = get_task_logger(__name__)

class GDDVisionUploader(VisionUploader):
    serializer_class = GDDVisionExportSerializer

    def get_endpoint(self):
        return getattr(settings, 'EZHACT_PD_VISION_URL', None)

    def validate_instance(self):
        """
        # PD is not in Development, Review, Signature.
        # We also need to make sure that this pd has GDDActivities.
        # The PD cannot be and amendment "amendment_open" will not pass validation.
        """
        if self.instance.status in [GDD.DRAFT, GDD.REVIEW, GDD.SIGNATURE]:
            return False

        if not GDDActivity.objects.filter(key_intervention__result_link__gdd=self.instance).exists():
            return False

        # amendment intervention
        if self.instance.in_amendment:
            return False

        # intervention with open amendment
        if self.instance.amendments.filter(is_active=True).exists():
            return False

        return True

@app.task
def send_gdd_to_vision(tenant_name: str, gdd_pk: int, retry_counter=0):
    original_tenant = connection.tenant

    try:
        tenant = get_tenant_model().objects.get(name=tenant_name)
        connection.set_tenant(tenant)

        # get just basic information. in case validation fail it will save us many db queries
        gdd = GDD.objects.get(pk=gdd_pk)
        logger.info(f'Starting {gdd} upload to vision')

        synchronizer = GDDVisionUploader(gdd)
        if not synchronizer.is_valid():
            logger.info('Instance is not ready to be synchronized')
            return

        # reload intervention with prefetched relations for serialization
        synchronizer.instance = GDD.objects.detail_qs().get(pk=gdd_pk)
        response = synchronizer.sync()
        if response is None:
            logger.warning('Synchronizer internal check failed')
            return

        status_code, _data = response
        if status_code in [200, 201]:
            logger.info('Completed pd synchronization')
            return

        if retry_counter < 2:
            logger.info(f'Received {status_code} from vision synchronizer. retrying')
            send_gdd_to_vision.apply_async(
                (tenant.name, gdd_pk,),
                {'retry_counter': retry_counter + 1},
                eta=timezone.now() + datetime.timedelta(minutes=1 + retry_counter)
            )
        else:
            logger.exception(f'Received {status_code} from vision synchronizer after 3 attempts. '
                             f'PD number: {gdd_pk}. Business area code: {tenant.business_area_code}')
    finally:
        connection.set_tenant(original_tenant)
