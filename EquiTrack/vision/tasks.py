
from django.db import connection
from django.utils import timezone

from celery.utils.log import get_task_logger

from EquiTrack.celery import app, send_to_slack
from partners.models import PartnerOrganization
from tpm.tpmpartners.models import TPMPartner
from users.models import Country
from vision.adapters.funding import FundCommitmentSynchronizer, FundReservationsSynchronizer
from vision.adapters.partner import PartnerSynchronizer
from vision.adapters.programme import ProgrammeSynchronizer, RAMSynchronizer
from vision.adapters.purchase_order import POSynchronizer
from vision.adapters.tpm_adapter import TPMPartnerSynchronizer
from vision.exceptions import VisionException

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


# Not scheduled by any code in this repo, but by other means, so keep it around.
# It catches all exceptions internally and keeps going on to the next partner, so
# no need to have celery retry it on exceptions.
# TODO: Write some tests for it!
@app.task
def update_all_partners(country_name=None):
    logger.info(u'Starting update HACT values for partners')
    countries = Country.objects.filter(vision_sync_enabled=True)
    if country_name is not None:
        countries = countries.filter(name=country_name)
    for country in countries:
        connection.set_tenant(country)
        logger.info(u'Updating {}'.format(country.name))
        partners = PartnerOrganization.objects.all()
        for partner in partners:
            try:
                PartnerOrganization.planned_visits(partner)
                PartnerOrganization.programmatic_visits(partner)
                PartnerOrganization.spot_checks(partner)
                PartnerOrganization.audits_completed(partner)

            except Exception:
                logger.exception(u'Exception {} {}'.format(partner.name, partner.hact_values))


# Not scheduled by any code in this repo, but by other means, so keep it around.
# Continues on to the next country on any VisionException, so no need to have
# celery retry it in that case.
# TODO: Write some tests for it!
@app.task
def update_purchase_orders(country_name=None):
    logger.info(u'Starting update values for purchase order')
    countries = Country.objects.filter(vision_sync_enabled=True)
    processed = []
    if country_name is not None:
        countries = countries.filter(name=country_name)
    for country in countries:
        connection.set_tenant(country)
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


@app.task
def update_tpm_partners(country_name=None):
    logger.info(u'Starting update values for TPM partners')
    countries = Country.objects.filter(vision_sync_enabled=True)
    processed = []
    if country_name is not None:
        countries = countries.filter(name=country_name)
    for country in countries:
        connection.set_tenant(country)
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
