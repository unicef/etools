from celery.utils.log import get_task_logger
# Not scheduled by any code in this repo, but by other means, so keep it around.
# Continues on to the next country on any VisionException, so no need to have
# celery retry it in that case.
from django_tenants.utils import get_public_schema_name
from unicef_vision.exceptions import VisionException

from etools.applications.audit.purchase_order.synchronizers import POSynchronizer
from etools.applications.users.models import Country
from etools.config.celery import app

logger = get_task_logger(__name__)


@app.task
def update_purchase_orders():
    logger.info('Starting update values for purchase order')
    country = Country.objects.get(schema_name=get_public_schema_name())
    processed = []
    try:
        logger.info('Starting purchase order update for country {}'.format(
            country.name
        ))
        POSynchronizer(country.business_area_code).sync()
        processed.append(country.name)
        logger.info("Update finished successfully for {}".format(country.name))
    except VisionException:
        logger.exception("{} sync failed".format(POSynchronizer.__name__))
        # Keep going to the next country
    logger.info('Purchase orders synced successfully for {}.'.format(', '.join(processed)))
