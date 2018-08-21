from celery.utils.log import get_task_logger

# Not scheduled by any code in this repo, but by other means, so keep it around.
# Continues on to the next country on any VisionException, so no need to have
# celery retry it in that case.
from etools.applications.audit.purchase_order.synchronizers import POSynchronizer
from etools.applications.users.models import Country
from etools.applications.vision.exceptions import VisionException
from etools.config.celery import app

logger = get_task_logger(__name__)


@app.task
def update_purchase_orders(country_name=None):
    logger.info(u'Starting update values for purchase order')
    countries = Country.objects.filter(vision_sync_enabled=True)
    processed = []
    if country_name is not None:
        countries = countries.filter(name=country_name)
    for country in countries:
        try:
            logger.info(u'Starting purchase order update for country {}'.format(
                country.name
            ))
            POSynchronizer(country).sync()
            processed.append(country.name)
            logger.info(u"Update finished successfully for {}".format(country.name))
        except VisionException:
            logger.exception(u"{} sync failed".format(POSynchronizer.__name__))
            # Keep going to the next country
    logger.info(u'Purchase orders synced successfully for {}.'.format(u', '.join(processed)))
