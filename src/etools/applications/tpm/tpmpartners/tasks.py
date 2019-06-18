from celery.utils.log import get_task_logger
from django_tenants.utils import get_public_schema_name
from unicef_vision.exceptions import VisionException

from etools.applications.tpm.tpmpartners.models import TPMPartner
from etools.applications.tpm.tpmpartners.synchronizers import TPMPartnerSynchronizer
from etools.applications.users.models import Country
from etools.config.celery import app

logger = get_task_logger(__name__)


@app.task
def update_tpm_partners():
    logger.info('Starting update values for TPM partners')
    processed = []
    country = Country.objects.get(schema_name=get_public_schema_name())
    try:
        logger.info('Starting TPM partners update for country {}'.format(
            country.name
        ))
        for partner in TPMPartner.objects.all():
            TPMPartnerSynchronizer(
                business_area_code=country.business_area_code,
                object_number=partner.vendor_number
            ).sync()
        processed.append(country.name)
        logger.info("Update finished successfully for {}".format(country.name))
    except VisionException:
        logger.exception("{} sync failed".format(TPMPartnerSynchronizer.__name__))
    logger.info('TPM Partners synced successfully for {}.'.format(', '.join(processed)))
