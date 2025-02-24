from django.db import connection
from django.utils import timezone

from celery.utils.log import get_task_logger
from unicef_vision.exceptions import VisionException

from etools.applications.funds.synchronizers import FundReservationsSynchronizer
from etools.applications.governments.synchronizers import EWPsSynchronizer
from etools.applications.partners.synchronizers import DirectCashTransferSynchronizer, PartnerSynchronizer
from etools.applications.reports.synchronizers import ProgrammeSynchronizer, RAMSynchronizer
from etools.applications.users.models import Country
from etools.config.celery import app, send_to_slack

PUBLIC_SYNC_HANDLERS = {}


SYNC_HANDLERS = {
    'programme': ProgrammeSynchronizer,
    'ram': RAMSynchronizer,
    'partner': PartnerSynchronizer,
    'fund_reservation': FundReservationsSynchronizer,
    # 'fund_commitment': FundCommitmentSynchronizer,
    'dct': DirectCashTransferSynchronizer,
    'ewp': EWPsSynchronizer,
}


logger = get_task_logger(__name__)


@app.task
def vision_sync_task(business_area_code=None, synchronizers=SYNC_HANDLERS.keys()):
    """
    Do the vision sync for all countries that have vision_sync_enabled=True,
    or just the named country.  Defaults to SYNC_HANDLERS but a
    different iterable of handlers can be passed in.
    """
    # Not invoked as a task from code in this repo, but it is scheduled
    # by other means, so it's really a Celery task.

    global_synchronizers = [handler for handler in synchronizers if SYNC_HANDLERS[handler].GLOBAL_CALL]
    tenant_synchronizers = [handler for handler in synchronizers if not SYNC_HANDLERS[handler].GLOBAL_CALL]

    country_filter_dict = {
        'vision_sync_enabled': True
    }
    if business_area_code:
        country_filter_dict['business_area_code'] = business_area_code
    countries = Country.objects.filter(**country_filter_dict)

    if not business_area_code or business_area_code == '0':  # public schema
        for handler in global_synchronizers:
            sync_handler.delay(business_area_code, handler)
    for country in countries:
        connection.set_tenant(country)
        for handler in tenant_synchronizers:
            sync_handler.delay(country.business_area_code, handler)
        country.vision_last_synced = timezone.now()
        country.save()

    text = 'Created tasks for the following countries: {} and synchronizers: {}'.format(
        ',\n '.join([country.name for country in countries]),
        ',\n '.join([synchronizer for synchronizer in synchronizers])
    )
    send_to_slack(text)
    logger.info(text)


@app.task(bind=True, autoretry_for=(VisionException,), retry_kwargs={'max_retries': 1})
def sync_handler(self, business_area_code, handler):
    """
    Run .sync() on one handler for one country.
    """
    # Scheduled from vision_sync_task() (above).
    logger.info('Starting vision sync handler {} for country {}'.format(handler, business_area_code))
    try:
        country = Country.objects.get(business_area_code=business_area_code)
    except Country.DoesNotExist:
        logger.error("{} sync failed, Could not find a Country with this business area code: {}".format(
            handler, business_area_code
        ))
        # No point in retrying if there's no such country
    else:
        try:
            if handler == "programme":
                SYNC_HANDLERS[handler](business_area_code=country.business_area_code, cycle="all").sync()
            else:
                SYNC_HANDLERS[handler](business_area_code=country.business_area_code).sync()
            logger.info("{} sync successfully for {} [{}]".format(handler, country.name, business_area_code))

        except VisionException:
            # Catch and log the exception so we're aware there's a problem.
            logger.exception("{} sync failed, Country: {}".format(
                handler, business_area_code
            ))
            # The 'autoretry_for' in the task decorator tells Celery to
            # retry this a few times on VisionExceptions, so just re-raise it
            raise
