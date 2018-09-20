from celery.utils.log import get_task_logger

from etools.applications.tpm.tpmpartners.models import TPMPartner
from etools.applications.tpm.tpmpartners.synchronizers import TPMPartnerSynchronizer
from etools.applications.users.models import Country
from etools.applications.vision.exceptions import VisionException
from etools.config.celery import app

logger = get_task_logger(__name__)


@app.task
def update_tpm_partners(country_name=None):
    logger.info(u'Starting update values for TPM partners')
    countries = Country.objects.filter(vision_sync_enabled=True)
    processed = []
    if country_name is not None:
        countries = countries.filter(name=country_name)
    for country in countries:
        try:
            logger.info(u'Starting TPM partners update for country {}'.format(
                country.name
            ))
            for partner in TPMPartner.objects.all():
                TPMPartnerSynchronizer(
                    country=country,
                    object_number=partner.vendor_number
                ).sync()
            processed.append(country.name)
            logger.info(u"Update finished successfully for {}".format(country.name))
        except VisionException:
            logger.exception(u"{} sync failed".format(TPMPartnerSynchronizer.__name__))
    logger.info(u'TPM Partners synced successfully for {}.'.format(u', '.join(processed)))
