
from datetime import datetime

from django.db import connection, transaction

from celery.utils.log import get_task_logger
from unicef_notification.utils import send_notification_with_template
from unicef_vision.exceptions import VisionException

from etools.applications.hact.models import AggregateHact
from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.models import Country
from etools.applications.vision.models import VisionSyncLog
from etools.config.celery import app
from etools.libraries.djangolib.utils import get_environment

logger = get_task_logger(__name__)


@app.task
def update_hact_for_country(business_area_code):
    country = Country.objects.get(business_area_code=business_area_code)
    log = VisionSyncLog(
        country=country,
        handler_name='HactSynchronizer'
    )
    connection.set_tenant(country)
    logger.info('Set country {}'.format(business_area_code))
    hact_updated_partner_list = []
    try:
        partners = PartnerOrganization.objects.hact_active()
        for partner in partners:
            logger.debug('Updating Partner {}'.format(partner.name))
            partner.planned_visits_to_hact()
            partner.programmatic_visits()
            partner.spot_checks()
            partner.audits_completed()
            partner.hact_support()
            updated = partner.update_min_requirements()
            if updated:
                hact_updated_partner_list.append(partner.name)

    except Exception as e:
        logger.info('HACT Sync', exc_info=True)
        log.exception_message = e
        raise VisionException
    else:
        log.total_records = partners.count()
        log.total_processed = partners.count()
        log.successful = True
    finally:
        log.save()
    if hact_updated_partner_list:
        notify_hact_update.delay(hact_updated_partner_list)


@app.task
def update_hact_values(*args, **kwargs):

    schema_names = kwargs.get('schema_names', [None])[0]
    logger.info('Hact Freeze Task process started')
    countries = Country.objects.exclude(schema_name='public')
    if schema_names:
        countries = countries.filter(schema_name__in=schema_names.split(','))
    for country in countries:
        update_hact_for_country.delay(country.business_area_code)
    logger.info('Hact Freeze Task generated all tasks')


@app.task
def update_aggregate_hact_values(*args, **kwargs):
    logger.info('Hact Aggregator Task process started')

    schema_names = kwargs.get('schema_names', [None])[0]
    countries = Country.objects.exclude(schema_name='public')
    if schema_names:
        countries = countries.filter(schema_name__in=schema_names.split(','))
    for country in countries:
        connection.set_tenant(country)
        with transaction.atomic():
            aggregate_hact, _ = AggregateHact.objects.get_or_create(year=datetime.today().year)
            try:
                aggregate_hact.update()
            except BaseException:
                logger.exception(country)

    logger.info('Hact Aggregator Task process finished')


@app.task
def notify_hact_update(partner_list):
    email_context = {
        'partners': partner_list,
        'environment': get_environment(),
    }
    recipients = set(['ddinicola@unicef.org', ])  # WIP
    send_notification_with_template(
        recipients=list(recipients),
        template_name='partners/hact_updated',
        context=email_context
    )
