import datetime
import time

from django.db import connection

from celery.utils.log import get_task_logger

from EquiTrack.celery import app, send_to_slack
from partners.models import PartnerOrganization
from users.models import Country
from vision.adapters.publics_adapter import CurrencySyncronizer, TravelAgenciesSyncronizer, CostAssignmentsSyncronizer
from vision_data_synchronizer import VisionException
from vision.adapters.programme import ProgrammeSynchronizer, RAMSynchronizer
from vision.adapters.partner import PartnerSynchronizer
from vision.adapters.funding import (
    FundingSynchronizer,
    FundReservationsSynchronizer,
    FundCommitmentSynchronizer,
    DCTSynchronizer,
)
from vision.models import VisionSyncLog


PUBLIC_SYNC_HANDLERS = []


SYNC_HANDLERS = [
    # ProgrammeSynchronizer,
    # RAMSynchronizer,
    # PartnerSynchronizer,
    # FundingSynchronizer,
    FundReservationsSynchronizer,
    FundCommitmentSynchronizer,
    #DCTSynchronizer
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
def sync(country_name=None):
    processed = []
    countries = Country.objects.filter(vision_sync_enabled=True)
    if country_name is not None:
        countries = countries.filter(name=country_name)

    global_handlers = [handler for handler in SYNC_HANDLERS if handler.GLOBAL_CALL]
    tenant_handlers = [handler for handler in SYNC_HANDLERS if not handler.GLOBAL_CALL]

    public_tenant = Country.objects.get(schema_name='public')
    for handler in global_handlers:
        try:
            logger.info('Starting vision sync handler {} for country {}'.format(
                handler.__name__, public_tenant.name
            ))
            handler(public_tenant).sync()
            logger.info("{} sync successfully".format(handler.__name__))

        except VisionException as e:
            logger.error("{} sync failed, Reason: {}".format(
                handler.__name__, e.message
            ))

    for country in countries:
        connection.set_tenant(country)
        for handler in tenant_handlers:
            try:
                logger.info('Starting vision sync handler {} for country {}'.format(
                    handler.__name__, country.name
                ))
                handler(country).sync()
                logger.info("{} sync successfully".format(handler.__name__))

            except VisionException as e:
                logger.error("{} sync failed, Reason: {}".format(
                    handler.__name__, e.message
                ))
        country.vision_last_synced = datetime.datetime.now()
        country.save()
        processed.append(country)

    text = 'Processed the following countries during sync: {}'.format(
        ',\n '.join([country.name for country in processed])
    )
    send_to_slack(text)
    logger.info(text)


@app.task
def update_partners(country_name=None):
    print 'Starting update HACT values for partners'
    countries = Country.objects.filter(vision_sync_enabled=True)
    if country_name is not None:
        countries = countries.filter(name=country_name)
    for country in countries:
        connection.set_tenant(country)
        print country.name
        partners = PartnerOrganization.objects.all()
        for partner in partners:
            try:
                PartnerOrganization.micro_assessment_needed(partner)
                if partner.total_ct_cp > 500000:
                    PartnerOrganization.audit_needed(partner)
            except Exception as e:
                print partner.name
                print partner.hact_values
                print e.message


@app.task
def update_all_partners(country_name=None):
    print 'Starting update HACT values for partners'
    countries = Country.objects.filter(vision_sync_enabled=True)
    if country_name is not None:
        countries = countries.filter(name=country_name)
    for country in countries:
        connection.set_tenant(country)
        print country.name
        partners = PartnerOrganization.objects.all()
        for partner in partners:
            try:
                PartnerOrganization.planned_cash_transfers(partner)
                PartnerOrganization.micro_assessment_needed(partner)
                PartnerOrganization.audit_needed(partner)
                PartnerOrganization.audit_done(partner)
                PartnerOrganization.planned_visits(partner)
                PartnerOrganization.programmatic_visits(partner)
                PartnerOrganization.spot_checks(partner)
                PartnerOrganization.follow_up_flags(partner)

            except Exception as e:
                print partner.name
                print partner.hact_values
                print e.message
