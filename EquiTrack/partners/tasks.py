
import csv
import datetime
import itertools

from django.conf import settings
from django.core.mail.message import EmailMessage
from django.db import connection, transaction
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.db.utils import six

from celery.utils.log import get_task_logger
from six import StringIO

from EquiTrack.celery import app
from notification.utils import send_notification_using_email_template
from partners.models import Agreement, Intervention, PartnerOrganization
from partners.utils import copy_all_attachments
from partners.validation.agreements import AgreementValid
from partners.validation.interventions import InterventionValid
from users.models import Country, User

logger = get_task_logger(__name__)

# _INTERVENTION_ENDING_SOON_DELTAS is used by intervention_notification_ending(). Notifications will be sent
# about each interventions ending {delta} days from now.
_INTERVENTION_ENDING_SOON_DELTAS = (15, 30)


def get_intervention_context(intervention):
    '''Return a dict formatting some details about the intervention.

    Helper function for some of the notification tasks in this file.
    '''
    return {
        'number': six.text_type(intervention),
        'partner': intervention.agreement.partner.name,
        'start_date': six.text_type(intervention.start),
        'url': 'https://{}/pmp/interventions/{}/details'.format(settings.HOST, intervention.id),
        'unicef_focal_points': [focal_point.email for focal_point in intervention.unicef_focal_points.all()]
    }


@app.task
def agreement_status_automatic_transition():
    '''Check validity and save changed status (if any) for agreements that meet all of the following criteria --
        - signed
        - end date is after today
        - type != SSFA
    '''
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _make_agreement_status_automatic_transitions(country.name)


def _make_agreement_status_automatic_transitions(country_name):
    '''Implementation core of agreement_status_automatic_transition() (q.v.)'''
    logger.info('Starting agreement auto status transition for country {}'.format(country_name))

    admin_user = User.objects.get(username=settings.TASK_ADMIN_USER)

    # these are agreements that are not even valid within their own status
    # compiling a list of them to send to an admin or save somewhere in the future
    bad_agreements = []

    # SSFAs don't transition automatically unless they transition based on the intervention.
    signed_ended_agrs = Agreement.objects.filter(status=Agreement.SIGNED, end__lt=datetime.date.today())\
        .exclude(agreement_type=Agreement.SSFA)
    processed = 0

    for agr in signed_ended_agrs:
        old_status = agr.status
        # this function mutates agreement
        with transaction.atomic():
            validator = AgreementValid(agr, user=admin_user, disable_rigid_check=True)
            if validator.is_valid:
                if agr.status != old_status:
                    # this one transitioned forward
                    agr.save()
                    processed += 1
            else:
                bad_agreements.append(agr)

    logger.error('Bad agreements {}'.format(len(bad_agreements)))
    logger.error('Bad agreements ids: ' + ' '.join(six.text_type(a.id) for a in bad_agreements))
    logger.info('Total agreements {}'.format(signed_ended_agrs.count()))
    logger.info("Transitioned agreements {} ".format(processed))


@app.task
def intervention_status_automatic_transition():
    '''Check validity and save changed status (if any) for interventions that meet all of the following criteria --
        - active
        - end date is yesterday

    Also for interventions that meet all of the following criteria --
        - ended
        - total outstanding_amt == 0
        - total_amt == actual_amt
    '''
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _make_intervention_status_automatic_transitions(country.name)


@transaction.atomic
def _make_intervention_status_automatic_transitions(country_name):
    '''Implementation core of intervention_status_automatic_transition() (q.v.)'''
    logger.info('Starting intervention auto status transition for country {}'.format(country_name))

    admin_user = User.objects.get(username=settings.TASK_ADMIN_USER)

    # these are agreements that are not even valid within their own status
    # compiling a list of them to send to an admin or save somewhere in the future
    bad_interventions = []

    active_ended = Intervention.objects.filter(status=Intervention.ACTIVE,
                                               end__lt=datetime.date.today())

    # get all the interventions for which their status is endend and total otustanding_amt is 0 and
    # actual_amt is the same as the total_amt

    qs = Intervention.objects\
        .prefetch_related('frs')\
        .filter(status=Intervention.ENDED)\
        .annotate(frs_total_outstanding=Sum('frs__outstanding_amt'),
                  frs_total_actual_amt=Sum('frs__actual_amt'),
                  frs_intervention_amt=Sum('frs__intervention_amt'))\
        .filter(frs_total_outstanding=0, frs_total_actual_amt=F('frs_intervention_amt'))

    processed = 0

    for intervention in itertools.chain(active_ended, qs):
        old_status = intervention.status
        with transaction.atomic():
            # this function mutates the intervention
            validator = InterventionValid(intervention, user=admin_user, disable_rigid_check=True)
            if validator.is_valid:
                if intervention.status != old_status:
                    # this one transitioned forward
                    intervention.save()
                    processed += 1
            else:
                bad_interventions.append(intervention)

    logger.error('Bad interventions {}'.format(len(bad_interventions)))
    logger.error('Bad interventions ids: ' + ' '.join(six.text_type(a.id) for a in bad_interventions))
    logger.info('Total interventions {}'.format(active_ended.count() + qs.count()))
    logger.info("Transitioned interventions {} ".format(processed))


@app.task
def intervention_notification_signed_no_frs():
    '''Send notifications for interventions that meet all of the following criteria --
        - signed
        - ending today or in the future
        - have no related FRS

    This should only run once a week.
    '''
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _notify_of_signed_interventions_with_no_frs(country.name)


def _notify_of_signed_interventions_with_no_frs(country_name):
    '''Implementation core of intervention_notification_signed_no_frs() (q.v.)'''
    logger.info('Starting intervention signed but no FRs notifications for country {}'.format(country_name))

    signed_interventions = Intervention.objects.filter(status=Intervention.SIGNED,
                                                       start__gte=datetime.date.today(),
                                                       frs__isnull=True)

    for intervention in signed_interventions:
        email_context = get_intervention_context(intervention)
        send_notification_using_email_template(
            sender=intervention,
            recipients=email_context['unicef_focal_points'],
            email_template_name="partners/partnership/signed/frs",
            context=email_context
        )


@app.task
def intervention_notification_ended_fr_outstanding():
    '''Send notifications for interventions that meet all of the following criteria --
        - ended
        - total_frs['total_actual_amt'] != total_frs['total_frs_amt']

    This will run every 2 weeks
    '''
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _notify_of_ended_interventions_with_mismatched_frs(country.name)


def _notify_of_ended_interventions_with_mismatched_frs(country_name):
    '''Implementation core of intervention_notification_ended_fr_outstanding() (q.v.)'''
    logger.info('Starting intervention signed but FRs Amount and actual '
                'do not match notifications for country {}'.format(country_name))

    ended_interventions = Intervention.objects.filter(status=Intervention.ENDED)
    for intervention in ended_interventions:
        if intervention.total_frs['total_actual_amt'] != intervention.total_frs['total_frs_amt']:
            email_context = get_intervention_context(intervention)
            send_notification_using_email_template(
                sender=intervention,
                recipients=email_context['unicef_focal_points'],
                email_template_name="partners/partnership/ended/frs/outstanding",
                context=email_context
            )


@app.task
def intervention_notification_ending():
    '''Send notifications for interventions that will end soon, where "soon" are the # of days from today defined
    in _INTERVENTION_ENDING_SOON_DELTAS.

    This will run every 24 hours.
    '''
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _notify_interventions_ending_soon(country.name)


def _notify_interventions_ending_soon(country_name):
    '''Implementation core of intervention_notification_ending() (q.v.)'''
    logger.info('Starting interventions almost ending notifications for country {}'.format(country_name))

    today = datetime.date.today()

    notify_end_dates = [today + datetime.timedelta(days=delta) for delta in (_INTERVENTION_ENDING_SOON_DELTAS)]

    interventions = Intervention.objects.filter(status=Intervention.ACTIVE, end__in=notify_end_dates)
    interventions = interventions.prefetch_related('unicef_focal_points', 'agreement', 'agreement__partner')

    for intervention in interventions:
        email_context = get_intervention_context(intervention)
        email_context["days"] = str((intervention.end - today).days)
        send_notification_using_email_template(
            sender=intervention,
            recipients=email_context['unicef_focal_points'],
            email_template_name="partners/partnership/ending",
            context=email_context
        )


@app.task
def pmp_indicator_report():
    base_url = 'https://etools.unicef.org'
    countries = Country.objects.exclude(schema_name__in=['public', 'uat', 'frg'])
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
        'Sum of all FR planned amount',
        'Core value attached',
        'Partner Link',
        'Intervention Link',
    ]
    csvfile = StringIO()
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for country in countries:
        connection.set_tenant(Country.objects.get(name=country.name))
        logger.info(u'Running on %s' % country.name)
        for partner in PartnerOrganization.objects.filter():
            for intervention in Intervention.objects.filter(
                    agreement__partner=partner).select_related('planned_budget'):
                planned_budget = getattr(intervention, 'planned_budget', None)
                writer.writerow({
                    'Country': country,
                    'Partner Name': six.string_types(partner).decode('unicode_escape').encode('ascii', 'ignore'),
                    'Partner Type': partner.cso_type,
                    'PD / SSFA ref': intervention.number.encode('utf-8').replace(',', '-'),
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
                    'FR numbers against PD / SSFA': u' - '.join([
                        (fh.fr_number.encode('utf-8')) for fh in intervention.frs.all()]),
                    'Sum of all FR planned amount': intervention.frs.aggregate(
                        total=Coalesce(Sum('intervention_amt'), 0))['total'],
                    'Core value attached': True if partner.core_values_assessment else False,
                    'Partner Link': '{}/pmp/partners/{}/details'.format(base_url, partner.pk),
                    'Intervention Link': '{}/pmp/interventions/{}/details'.format(base_url, intervention.pk),
                })

    mail = EmailMessage('PMP Indicator Report', 'Report generated', 'etools-reports@unicef.org', settings.REPORT_EMAILS)
    mail.attach('pmp_indicators.csv', csvfile.getvalue(), 'text/csv')
    mail.send()


@app.task
def copy_attachments():
    """Copy all partner app attachments"""
    copy_all_attachments()
