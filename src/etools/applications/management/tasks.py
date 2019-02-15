import logging
from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Sum
from django.db.models.functions import Coalesce

from dateutil.relativedelta import relativedelta

from etools.applications.EquiTrack.util_scripts import set_country
from etools.applications.audit.models import Audit, Engagement, MicroAssessment, SpecialAudit, SpotCheck
from etools.applications.management.issues.checks import recheck_all_open_issues, run_all_checks
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.users.models import Country
from etools.config.celery import app

logger = logging.getLogger(__name__)


@app.task
def run_all_checks_task():
    """
    Run all configured IssueChecks against the entire database.
    """
    run_all_checks()


@app.task
def recheck_all_open_issues_task():
    """
    Recheck all unresolved FlaggedIssue objects for resolution.
    """
    recheck_all_open_issues()


@app.task
def send_test_email(*args, **kwargs):
    """Task which send a test email"""

    logger.info('Test send email task started')

    subject = kwargs.get('subject', ['Test Subject'])[0]
    message = kwargs.get('message', ['Test Message'])[0]
    from_email = kwargs.get('from_email', ['from_email@unicef.org'])[0]
    user_email = kwargs.get('user_email', [])
    recipient_list = kwargs.get('recipient_list', [])
    if recipient_list:
        recipient_list = recipient_list[0].split(',')

    recipient_list.extend(user_email)

    send_mail(subject, message, from_email, recipient_list)

    logger.info('Test send email task finished')


@app.task
def user_report(writer, **kwargs):

    start_date = kwargs.get('start_date', None)
    if start_date:
        start_date = datetime.strptime(start_date.pop(), '%Y-%m-%d')
    else:
        start_date = date.today() + relativedelta(months=-1)

    countries = kwargs.get('countries', None)
    qs = Country.objects.exclude(schema_name__in=['public', 'uat', 'frg'])
    if countries:
        qs = qs.filter(schema_name__in=countries.pop().split(','))
    fieldnames = ['Country', 'Total Users', 'Unicef Users', 'Last month Users', 'Last month Unicef Users']
    dict_writer = writer(fieldnames=fieldnames)
    dict_writer.writeheader()

    for country in qs:
        dict_writer.writerow({
            'Country': country,
            'Total Users': get_user_model().objects.filter(profile__country=country).count(),
            'Unicef Users': get_user_model().objects.filter(
                profile__country=country,
                email__endswith='@unicef.org'
            ).count(),
            'Last month Users': get_user_model().objects.filter(
                profile__country=country,
                last_login__gte=start_date
            ).count(),
            'Last month Unicef Users': get_user_model().objects.filter(
                profile__country=country,
                email__endswith='@unicef.org',
                last_login__gte=start_date
            ).count(),
        })


@app.task
def pmp_indicator_report(writer, **kwargs):
    base_url = 'https://etools.unicef.org'
    countries = kwargs.get('countries', None)
    qs = Country.objects.exclude(schema_name__in=['public', 'uat', 'frg'])
    if countries:
        qs = qs.filter(schema_name__in=countries.pop().split(','))
    fieldnames = [
        'Country',
        'Partner Name',
        'Partner Type',
        'PD / SSFA ref',
        'PD / SSFA status',
        'PD / SSFA start date',
        'PD / SSFA creation date',
        'PD / SSFA end date',
        'UNICEF US$ Cash contribution',
        'UNICEF US$ Supply contribution',
        'Total Budget',
        'UNICEF Budget',
        'Currency',
        'Partner Contribution',
        'Unicef Cash',
        'In kind Amount',
        'Total',
        'FR numbers against PD / SSFA',
        'FR currencies',
        'Sum of all FR planned amount',
        'Core value attached',
        'Partner Link',
        'Intervention Link',
    ]

    dict_writer = writer(fieldnames=fieldnames)
    dict_writer.writeheader()

    for country in qs:
        set_country(country.name)
        logger.info('Running on %s' % country.name)
        for partner in PartnerOrganization.objects.prefetch_related('core_values_assessments'):
            for intervention in Intervention.objects.filter(
                    agreement__partner=partner).select_related('planned_budget'):
                planned_budget = getattr(intervention, 'planned_budget', None)
                fr_currencies = intervention.frs.all().values_list('currency', flat=True).distinct()
                has_assessment = bool(getattr(partner.current_core_value_assessment, 'assessment', False))
                dict_writer.writerow({
                    'Country': country,
                    'Partner Name': str(partner),
                    'Partner Type': partner.cso_type,
                    'PD / SSFA ref': intervention.number.replace(',', '-'),
                    'PD / SSFA status': intervention.get_status_display(),
                    'PD / SSFA start date': intervention.start,
                    'PD / SSFA creation date': intervention.created,
                    'PD / SSFA end date': intervention.end,
                    'UNICEF US$ Cash contribution': intervention.total_unicef_cash,
                    'UNICEF US$ Supply contribution': intervention.total_in_kind_amount,
                    'Total Budget': intervention.total_budget,
                    'UNICEF Budget': intervention.total_unicef_budget,
                    'Currency': intervention.planned_budget.currency if planned_budget else '-',
                    'Partner Contribution': intervention.planned_budget.partner_contribution if planned_budget else '-',
                    'Unicef Cash': intervention.planned_budget.unicef_cash if planned_budget else '-',
                    'In kind Amount': intervention.planned_budget.in_kind_amount if planned_budget else '-',
                    'Total': intervention.planned_budget.total if planned_budget else '-',
                    'FR numbers against PD / SSFA': ' - '.join([fh.fr_number for fh in intervention.frs.all()]),
                    'FR currencies': ', '.join(fr for fr in fr_currencies),
                    'Sum of all FR planned amount': intervention.frs.aggregate(
                        total=Coalesce(Sum('intervention_amt'), 0))['total'] if fr_currencies.count() <= 1 else '-',
                    'Core value attached': has_assessment,
                    'Partner Link': '{}/pmp/partners/{}/details'.format(base_url, partner.pk),
                    'Intervention Link': '{}/pmp/interventions/{}/details'.format(base_url, intervention.pk),
                })


@app.task
def fam_report(writer, **kwargs):
    countries = kwargs.get('countries', None)
    start_date = kwargs.get('start_date', None)
    if start_date:
        start_date = datetime.strptime(start_date.pop(), '%Y-%m-%d')
    else:
        start_date = date.today() + relativedelta(months=-1)

    engagements = (SpotCheck, Audit, SpecialAudit, MicroAssessment)
    fieldnames = ['Country'] + ['{}-{}'.format(model._meta.verbose_name_raw, status_display)
                                for model in engagements for _, status_display in Engagement.STATUSES]
    dict_writer = writer(fieldnames=fieldnames)
    dict_writer.writeheader()

    qs = Country.objects.exclude(schema_name__in=['public', 'uat', 'frg'])
    if countries:
        qs = qs.filter(schema_name__in=countries.pop().split(','))

    for country in qs:
        set_country(country.name)
        row_dict = {'Country': country.name}
        for model in engagements:
            for status, status_display in Engagement.STATUSES:
                filter_dict = {
                    'status': status,
                    'start_date__month': start_date.month,
                    'start_date__year': start_date.year,
                }
                row_dict['{}-{}'.format(
                    model._meta.verbose_name_raw, status_display)] = model.objects.filter(**filter_dict).count()
        dict_writer.writerow(row_dict)
