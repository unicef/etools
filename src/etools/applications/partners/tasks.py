import datetime
import itertools

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models import F, Prefetch, Sum

from celery.utils.log import get_task_logger
from django_tenants.utils import get_tenant_model, schema_context
from unicef_notification.utils import send_notification_with_template

from etools.applications.partners.models import Agreement, Intervention, PartnerOrganization, PartnerStaffMember
from etools.applications.partners.prp_api import PRPAPI
from etools.applications.partners.serializers.prp_v1 import PRPPartnerOrganizationWithStaffMembersSerializer
from etools.applications.partners.utils import (
    copy_all_attachments,
    send_intervention_draft_notification,
    send_intervention_past_start_notification,
    send_pca_missing_notifications,
    send_pca_required_notifications,
    sync_partner_staff_member,
)
from etools.applications.partners.validation.agreements import AgreementValid
from etools.applications.partners.validation.interventions import InterventionValid
from etools.applications.users.models import Country
from etools.config.celery import app
from etools.libraries.djangolib.utils import get_environment
from etools.libraries.tenant_support.utils import every_country, run_on_all_tenants

logger = get_task_logger(__name__)

# _INTERVENTION_ENDING_SOON_DELTAS is used by intervention_notification_ending(). Notifications will be sent
# about each interventions ending {delta} days from now.
_INTERVENTION_ENDING_SOON_DELTAS = (15, 30, 60, 90)


def get_intervention_context(intervention):
    """Return a dict formatting some details about the intervention.

    Helper function for some of the notification tasks in this file.
    """
    return {
        'number': str(intervention),
        'partner': intervention.agreement.partner.name,
        'start_date': str(intervention.start),
        'url': '{}/pmp/interventions/{}/details'.format(settings.HOST, intervention.id),
        'unicef_focal_points': [focal_point.email for focal_point in intervention.unicef_focal_points.all()]
    }


@app.task
def agreement_status_automatic_transition():
    """Check validity and save changed status (if any) for agreements that meet all of the following criteria --
        - signed
        - end date is after today
        - type != SSFA
    """
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _make_agreement_status_automatic_transitions(country.name)


def _make_agreement_status_automatic_transitions(country_name):
    """Implementation core of agreement_status_automatic_transition() (q.v.)"""
    logger.info('Starting agreement auto status transition for country {}'.format(country_name))

    admin_user = get_user_model().objects.get(username=settings.TASK_ADMIN_USER)

    # these are agreements that are not even valid within their own status
    # compiling a list of them to send to an admin or save somewhere in the future
    bad_agreements = []

    # SSFAs don't transition automatically unless they transition based on the intervention.
    signed_ended_agrs = Agreement.objects.filter(
        status__in=[Agreement.DRAFT, Agreement.SIGNED],
        end__lt=datetime.date.today()
    ).exclude(agreement_type=Agreement.SSFA)
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
    logger.error('Bad agreements ids: ' + ' '.join(str(a.id) for a in bad_agreements))
    logger.info('Total agreements {}'.format(signed_ended_agrs.count()))
    logger.info("Transitioned agreements {} ".format(processed))


@app.task
def intervention_status_automatic_transition():
    """Check validity and save changed status (if any) for interventions that meet all of the following criteria --
        - active
        - end date is yesterday

    Also for interventions that meet all of the following criteria --
        - ended
        - total outstanding_amt == 0
        - total_amt == actual_amt
    """
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _make_intervention_status_automatic_transitions(country.name)


@transaction.atomic
def _make_intervention_status_automatic_transitions(country_name):
    """Implementation core of intervention_status_automatic_transition() (q.v.)"""
    logger.info('Starting intervention auto status transition for country {}'.format(country_name))

    admin_user = get_user_model().objects.get(username=settings.TASK_ADMIN_USER)
    bad_interventions = []
    active_ended = Intervention.objects.filter(status=Intervention.ACTIVE,
                                               end__lt=datetime.date.today())
    qs = Intervention.objects\
        .prefetch_related('frs')\
        .filter(status=Intervention.ENDED)\
        .annotate(frs_total_outstanding=Sum('frs__outstanding_amt_local'),
                  frs_total_actual_amt=Sum('frs__total_amt_local'),
                  frs_intervention_amt=Sum('frs__actual_amt_local'))\
        .filter(frs_total_outstanding=0, frs_total_actual_amt=F('frs_intervention_amt'))
    processed = 0
    for intervention in itertools.chain(active_ended, qs):
        old_status = intervention.status
        with transaction.atomic():
            validator = InterventionValid(intervention, user=admin_user, disable_rigid_check=True)
            if validator.is_valid:
                if intervention.status != old_status:
                    intervention.save()
                    processed += 1
            else:
                bad_interventions.append(intervention)

    logger.error('Bad interventions {}'.format(len(bad_interventions)))
    logger.error('Bad interventions ids: ' + ' '.join(str(a.id) for a in bad_interventions))
    logger.info('Total interventions {}'.format(active_ended.count() + qs.count()))
    logger.info("Transitioned interventions {} ".format(processed))


@app.task
def intervention_notification_signed_no_frs():
    """Send notifications for interventions that meet all of the following criteria --
        - signed
        - ending today or in the future
        - have no related FRS

    This should only run once a week.
    """
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _notify_of_signed_interventions_with_no_frs(country.name)


def _notify_of_signed_interventions_with_no_frs(country_name):
    """Implementation core of intervention_notification_signed_no_frs() (q.v.)"""
    logger.info('Starting intervention signed but no FRs notifications for country {}'.format(country_name))

    signed_interventions = Intervention.objects.filter(status=Intervention.SIGNED,
                                                       start__gte=datetime.date.today(),
                                                       frs__isnull=True)

    for intervention in signed_interventions:
        email_context = get_intervention_context(intervention)
        send_notification_with_template(
            sender=intervention,
            recipients=email_context['unicef_focal_points'],
            template_name="partners/partnership/signed/frs",
            context=email_context
        )


@app.task
def intervention_notification_ended_fr_outstanding():
    """Send notifications for interventions that meet all of the following criteria --
        - ended
        - total_frs['total_actual_amt'] != total_frs['total_frs_amt']

    This will run every 2 weeks
    """
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _notify_of_ended_interventions_with_mismatched_frs(country.name)


def _notify_of_ended_interventions_with_mismatched_frs(country_name):
    """Implementation core of intervention_notification_ended_fr_outstanding() (q.v.)"""
    logger.info('Starting intervention signed but FRs Amount and actual '
                'do not match notifications for country {}'.format(country_name))

    ended_interventions = Intervention.objects.filter(status=Intervention.ENDED)
    for intervention in ended_interventions:
        if intervention.total_frs['total_actual_amt'] != intervention.total_frs['total_frs_amt']:
            email_context = get_intervention_context(intervention)
            send_notification_with_template(
                sender=intervention,
                recipients=email_context['unicef_focal_points'],
                template_name="partners/partnership/ended/frs/outstanding",
                context=email_context
            )


@app.task
def intervention_notification_ending():
    """Send notifications for interventions that will end soon, where "soon" are the # of days from today defined
    in _INTERVENTION_ENDING_SOON_DELTAS.

    This will run every 24 hours.
    """
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _notify_interventions_ending_soon(country.name)


def _notify_interventions_ending_soon(country_name):
    """Implementation core of intervention_notification_ending() (q.v.)"""
    logger.info('Starting interventions almost ending notifications for country {}'.format(country_name))

    today = datetime.date.today()

    notify_end_dates = [today + datetime.timedelta(days=delta) for delta in _INTERVENTION_ENDING_SOON_DELTAS]

    interventions = Intervention.objects.filter(status=Intervention.ACTIVE, end__in=notify_end_dates)
    interventions = interventions.prefetch_related('unicef_focal_points', 'agreement', 'agreement__partner')

    for intervention in interventions:
        email_context = get_intervention_context(intervention)
        email_context["days"] = str((intervention.end - today).days)
        send_notification_with_template(
            sender=intervention,
            recipients=email_context['unicef_focal_points'],
            template_name="partners/partnership/ending",
            context=email_context
        )


@app.task
def copy_attachments(hours=25):
    """Copy all partner app attachments"""
    copy_all_attachments(hours=hours)


@app.task
def notify_partner_hidden(partner_pk, tenant_name):

    with schema_context(tenant_name):
        partner = PartnerOrganization.objects.get(pk=partner_pk)
        pds = Intervention.objects.filter(
            agreement__partner__name=partner.name,
            status__in=[Intervention.SIGNED, Intervention.ACTIVE, Intervention.ENDED]
        )
        if pds:
            email_context = {
                'partner_name': partner.name,
                'pds': ', '.join(pd.number for pd in pds),
                'environment': get_environment(),
            }
            emails_to_pd = [pd.unicef_focal_points.values_list('email', flat=True) for pd in pds]
            recipients = set(itertools.chain.from_iterable(emails_to_pd))

            send_notification_with_template(
                recipients=list(recipients),
                template_name='partners/blocked_partner',
                context=email_context
            )


@app.task
def check_pca_required():
    run_on_all_tenants(send_pca_required_notifications)


@app.task
def check_pca_missing():
    run_on_all_tenants(send_pca_missing_notifications)


@app.task
def check_intervention_draft_status():
    run_on_all_tenants(send_intervention_draft_notification)


@app.task
def check_intervention_past_start():
    run_on_all_tenants(send_intervention_past_start_notification)


@app.task
def sync_partner_to_prp(tenant: str, partner_id: int):
    tenant = get_tenant_model().objects.get(name=tenant)
    connection.set_tenant(tenant)

    partner = PartnerOrganization.objects.filter(id=partner_id).prefetch_related(
        Prefetch('staff_members', PartnerStaffMember.objects.filter(active=True))
    ).get()
    partner_data = PRPPartnerOrganizationWithStaffMembersSerializer(instance=partner).data
    PRPAPI().send_partner_data(tenant.business_area_code, partner_data)


@app.task
def sync_partners_staff_members_from_prp():
    api = PRPAPI()

    # remember where every particular partner is located for easier search
    partners_tenants_mapping = {}
    with every_country() as c:
        for country in c:
            connection.set_tenant(country)
            for partner in PartnerOrganization.objects.all():
                partners_tenants_mapping[(str(partner.id), partner.vendor_number)] = country

    for partner_data in PRPAPI().get_partners_list():
        key = (partner_data.external_id, partner_data.unicef_vendor_number)
        partner_tenant = partners_tenants_mapping.get(key)
        if not partner_tenant:
            continue

        connection.set_tenant(partner_tenant)
        partner = PartnerOrganization.objects.get(
            id=partner_data.external_id,
            vendor_number=partner_data.unicef_vendor_number
        )

        for staff_member_data in api.get_partner_staff_members(partner_data.id):
            sync_partner_staff_member(partner, staff_member_data)
