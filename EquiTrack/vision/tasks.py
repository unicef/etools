from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import connection
from django.utils import timezone

from celery.utils.log import get_task_logger

from EquiTrack.celery import app, send_to_slack
from users.models import Country
from vision.adapters.funding import FundCommitmentSynchronizer, FundReservationsSynchronizer
from vision.adapters.partner import PartnerSynchronizer
from vision.adapters.programme import ProgrammeSynchronizer, RAMSynchronizer
from vision.exceptions import VisionException

PUBLIC_SYNC_HANDLERS = []


SYNC_HANDLERS = [
    ProgrammeSynchronizer,
    RAMSynchronizer,
    PartnerSynchronizer,
    FundReservationsSynchronizer,
    FundCommitmentSynchronizer,
]


logger = get_task_logger(__name__)


def vision_sync_task(country_name=None, synchronizers=SYNC_HANDLERS):
    """
    Do the vision sync for all countries that have vision_sync_enabled=True,
    or just the named country.  Defaults to SYNC_HANDLERS but a
    different iterable of handlers can be passed in.
    """
    # Only invoked from management command and tests, not scheduled, as far as I can see,
    # so it's not really a task as far as Celery is concerned.

    global_synchronizers = [handler for handler in synchronizers if handler.GLOBAL_CALL]
    tenant_synchronizers = [handler for handler in synchronizers if not handler.GLOBAL_CALL]

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
        ',\n '.join([synchronizer.__name__ for synchronizer in synchronizers])
    )
    send_to_slack(text)
    logger.info(text)


@app.task(bind=True)
def sync_handler(self, country_name, handler):
    """
    Run .sync() on one handler for one country.
    """
    # Scheduled from vision_sync_task() (above).
    logger.info(u'Starting vision sync handler {} for country {}'.format(handler.__name__, country_name))
    try:
        country = Country.objects.get(name=country_name)
    except Country.DoesNotExist:
        logger.error(u"{} sync failed, Could not find a Country with this name: {}".format(
            handler.__name__, country_name
        ))
        # No point in retrying if there's no such country
    else:
        try:
            handler(country).sync()
            logger.info(u"{} sync successfully for {}".format(handler.__name__, country.name))

        except VisionException as e:
            logger.error(u"{} sync failed, Reason: {}, Country: {}".format(
                handler.__name__, e.message, country_name
            ))
            # This might be worth retrying.
            try:
                raise self.retry(exc=e)
            except VisionException:
                # We must have exceeded retries and Celery raised the original exception again.
                # We've already logged it.
                pass
