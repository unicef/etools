from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import connection, transaction

from celery.utils.log import get_task_logger
from unicef_vision.exceptions import VisionException

from etools.applications.audit.models import UNICEFAuditFocalPoint
from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.hact.models import AggregateHact, HactHistory
from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.models import Country
from etools.applications.vision.models import VisionSyncLog
from etools.config.celery import app
from etools.libraries.djangolib.utils import get_environment

logger = get_task_logger(__name__)


@app.task
def update_hact_for_country(business_area_code):
    updated_dict = {
        'programmatic_visits': 'PV',
        'spot_checks': 'SC',
        'audits': 'Audits',
    }
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
            partner.update_planned_visits_to_hact()
            partner.update_programmatic_visits()
            partner.update_spot_checks()
            partner.update_audits_completed()
            partner.update_hact_support()
            updated = partner.update_min_requirements()
            if updated:
                updated_string = ', '.join([updated_dict[item] for item in updated])
                hact_updated_partner_list.append((partner.vendor_number, partner.name, updated_string))

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
        notify_hact_update.delay(hact_updated_partner_list, country.id)


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
def update_audit_hact_count_for_country(business_area_code, starting_year):
    country = Country.objects.get(business_area_code=business_area_code)
    log = VisionSyncLog(
        country=country,
        handler_name='UpdateAuditHactCountSynchronizer'
    )
    connection.set_tenant(country)
    logger.info('Set country {}'.format(business_area_code))

    try:
        partners = PartnerOrganization.objects.hact_active()
        for partner in partners:
            logger.debug('Updating Partner {} on Audit Count'.format(partner.name))
            for year in range(int(starting_year), datetime.today().year + 1):
                audit_counts = partner.get_audits_completed_for_year(year)
                logger.debug('{} Audit Counts for year {}:'.format(audit_counts, year))
                hact_history, created = HactHistory.objects.get_or_create(partner=partner, year=year)
                if created or not hact_history.partner_values:
                    continue
                for index, li in enumerate(hact_history.partner_values):
                    if 'Audit Completed' in li:
                        existing_count = hact_history.partner_values[index][1]
                        if existing_count != audit_counts:
                            logger.debug('{} != {} Existing audit count is different from calculated, '
                                         'updating..'.format(existing_count, audit_counts))
                            hact_history.partner_values[index][1] = audit_counts
                            hact_history.save(update_fields=['partner_values'])
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


@app.task
def update_audit_hact_count(*args, **kwargs):

    schema_names = kwargs.get('schema_names', [None])[0]
    starting_year = kwargs.get('starting_year', [None])[0]

    logger.info('Update Audit Hact Counting process started')
    countries = Country.objects.exclude(schema_name='public')
    if schema_names:
        countries = countries.filter(schema_name__in=schema_names.split(','))
    for country in countries:
        update_audit_hact_count_for_country.delay(country.business_area_code, starting_year)
    logger.info('Update Audit Hact Counting finished.')


@app.task
def notify_hact_update(partner_list, country_id):
    email_context = {
        'partners': partner_list,
        'environment': get_environment(),
    }
    recipients = get_user_model().objects.filter(
        realms__group__name=UNICEFAuditFocalPoint.name,
        realms__country__id=country_id,
        realms__is_active=True,
        is_superuser=False,
    ).values_list('email', flat=True).distinct()
    send_notification_with_template(
        recipients=list(recipients),
        template_name='partners/hact_updated',
        context=email_context
    )
