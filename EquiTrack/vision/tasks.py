from __future__ import unicode_literals

import datetime
import time

from django.db import connection
from django.utils import timezone

from celery.utils.log import get_task_logger

from EquiTrack.celery import app, send_to_slack
from partners.models import PartnerOrganization
from users.models import Country
from vision.adapters.funding import FundCommitmentSynchronizer, FundReservationsSynchronizer
from vision.adapters.partner import PartnerSynchronizer
from vision.adapters.programme import ProgrammeSynchronizer, RAMSynchronizer
from vision.adapters.publics_adapter import CostAssignmentSynch
from vision.adapters.purchase_order import POSynchronizer
from vision.exceptions import VisionException
from vision.models import VisionSyncLog

PUBLIC_SYNC_HANDLERS = []


SYNC_HANDLERS = [
    ProgrammeSynchronizer,
    RAMSynchronizer,
    PartnerSynchronizer,
    FundReservationsSynchronizer,
    FundCommitmentSynchronizer,
]


logger = get_task_logger(__name__)


@app.task
def fake_task_delay():
    country = Country.objects.get(name="UAT")
    log = VisionSyncLog(
        country=country,
        handler_name="Fake Task Delay 300"
    )
    log.save()
    time.sleep(300)
    log.successful = True
    log.save()


@app.task
def fake_task_no_delay():
    country = Country.objects.get(name="UAT")
    log = VisionSyncLog(
        country=country,
        handler_name="Fake Task NoDelay 2"
    )
    time.sleep(2)
    log.successful = True
    log.save()


@app.task
def cost_assignment_sync(country_name=None):
    processed = []
    countries = Country.objects.filter(vision_sync_enabled=True)
    if country_name is not None:
        countries = countries.filter(name=country_name)

    for country in countries:
        connection.set_tenant(country)

        try:
            logger.info(u'Starting vision sync handler {} for country {}'.format(
                CostAssignmentSynch.__name__, country.name
            ))
            CostAssignmentSynch(country).sync()
            logger.info(u"{} sync successfully".format(CostAssignmentSynch.__name__))

        except VisionException:
            logger.exception(u"{} sync failed".format(CostAssignmentSynch.__name__))
        processed.append(country)


@app.task
def vision_sync_task(country_name=None, synchronizers=SYNC_HANDLERS):

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


@app.task
def sync_handler(country_name, handler):
    logger.info(u'Starting vision sync handler {} for country {}'.format(handler.__name__, country_name))
    try:
        country = Country.objects.get(name=country_name)
    except Country.DoesNotExist:
        logger.error(u"{} sync failed, Could not find a Country with this name: {}".format(
            handler.__name__, country_name
        ))
    else:
        try:
            handler(country).sync()
            logger.info(u"{} sync successfully for {}".format(handler.__name__, country.name))

        except VisionException:
            logger.exception("{} sync failed, Country: {}".format(handler.__name__, country_name))


@app.task
def sync(country_name=None, synchronizers=None):
    synchronizers = synchronizers or SYNC_HANDLERS
    processed = []
    countries = Country.objects.filter(vision_sync_enabled=True)
    if country_name is not None:
        countries = countries.filter(name=country_name)

    global_handlers = [handler for handler in synchronizers if handler.GLOBAL_CALL]
    tenant_handlers = [handler for handler in synchronizers if not handler.GLOBAL_CALL]

    public_tenant = Country.objects.get(schema_name='public')
    for handler in global_handlers:
        try:
            logger.info(u'Starting vision sync handler {} for country {}'.format(
                handler.__name__, public_tenant.name
            ))
            handler(public_tenant).sync()
            logger.info(u"{} sync successfully".format(handler.__name__))

        except VisionException:
            logger.exception("{} sync failed".format(handler.__name__))

    for country in countries:
        connection.set_tenant(country)
        for handler in tenant_handlers:
            try:
                logger.info(u'Starting vision sync handler {} for country {}'.format(
                    handler.__name__, country.name
                ))
                handler(country).sync()
                logger.info(u"{} sync successfully".format(handler.__name__))

            except VisionException:
                logger.exception("{} sync failed".format(handler.__name__))
        country.vision_last_synced = datetime.datetime.now()
        country.save()
        processed.append(country)

    text = u'Processed the following countries during sync: {}'.format(
        ',\n '.join([country.name for country in processed])
    )
    send_to_slack(text)
    logger.info(text)


@app.task
def update_all_partners(country_name=None):
    logger.info(u'Starting update HACT values for partners')
    countries = Country.objects.filter(vision_sync_enabled=True)
    if country_name is not None:
        countries = countries.filter(name=country_name)
    for country in countries:
        connection.set_tenant(country)
        logger.info(u'Updating '.format(country.name))
        partners = PartnerOrganization.objects.all()
        for partner in partners:
            try:
                PartnerOrganization.planned_visits(partner)
                PartnerOrganization.programmatic_visits(partner)
                PartnerOrganization.spot_checks(partner)

            except Exception:
                logger.exception(u'Exception {} {}'.format(partner.name, partner.hact_values))


@app.task
def update_purchase_orders(country_name=None):
    logger.info(u'Starting update values for purchase order')
    countries = Country.objects.filter(vision_sync_enabled=True)
    if country_name is not None:
        countries = countries.filter(name=country_name)
    for country in countries:
        connection.set_tenant(country)
        try:
            logger.info(u'Starting purchase order update for country {}'.format(
                country.name
            ))
            POSynchronizer(country).sync()
            logger.info(u"Update finished successfully for {}".format(country.name))
        except VisionException:
                logger.exception(u"{} sync failed".format(POSynchronizer.__name__))
