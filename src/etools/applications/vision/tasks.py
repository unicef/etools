from django.db import connection
from django.utils import timezone

from celery.utils.log import get_task_logger

from etools.applications.funds.synchronizers import FundReservationsSynchronizer, FundCommitmentSynchronizer
from etools.applications.partners.synchronizers import PartnerSynchronizer
from etools.applications.reports.synchronizers import ProgrammeSynchronizer, RAMSynchronizer
from etools.applications.users.models import Country
from etools.applications.vision.exceptions import VisionException
from etools.config.celery import app, send_to_slack

PUBLIC_SYNC_HANDLERS = {}


SYNC_HANDLERS = {
    'programme': ProgrammeSynchronizer,
    'ram': RAMSynchronizer,
    'partner': PartnerSynchronizer,
    'fund_reservation': FundReservationsSynchronizer,
    'fund_commitment': FundCommitmentSynchronizer,
}


logger = get_task_logger(__name__)


@app.task
def vision_sync_task(country_name=None, synchronizers=SYNC_HANDLERS.keys()):
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
    if country_name:
        country_filter_dict['name'] = country_name
    countries = Country.objects.filter(**country_filter_dict)

    if not country_name or country_name == 'Global':
        for handler in global_synchronizers:
            sync_handler.delay('Global', handler)
    for country in countries:
        connection.set_tenant(country)
        for handler in tenant_synchronizers:
            sync_handler.delay(country.name, handler)
        country.vision_last_synced = timezone.now()
        country.save()

    text = u'Created tasks for the following countries: {} and synchronizers: {}'.format(
        ',\n '.join([country.name for country in countries]),
        ',\n '.join([synchronizer for synchronizer in synchronizers])
    )
    send_to_slack(text)
    logger.info(text)


@app.task(bind=True, autoretry_for=(VisionException,), retry_kwargs={'max_retries': 1})
def sync_handler(self, country_name, handler):
    """
    Run .sync() on one handler for one country.
    """
    # Scheduled from vision_sync_task() (above).
    logger.info(u'Starting vision sync handler {} for country {}'.format(handler, country_name))
    try:
        country = Country.objects.get(name=country_name)
    except Country.DoesNotExist:
        logger.error(u"{} sync failed, Could not find a Country with this name: {}".format(
            handler, country_name
        ))
        # No point in retrying if there's no such country
    else:
        try:
            SYNC_HANDLERS[handler](country).sync()
            logger.info(u"{} sync successfully for {}".format(handler, country.name))

        except VisionException:
            # Catch and log the exception so we're aware there's a problem.
            logger.exception(u"{} sync failed, Country: {}".format(
                handler, country_name
            ))
            # The 'autoretry_for' in the task decorator tells Celery to
            # retry this a few times on VisionExceptions, so just re-raise it
            raise
