import datetime
import itertools

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.translation import gettext as _

from celery.utils.log import get_task_logger
from django_tenants.utils import get_tenant_model, schema_context
from requests import HTTPError
from unicef_snapshot.models import Activity
from unicef_vision.exceptions import VisionException
from unicef_vision.utils import get_data_from_insight

from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.partners.models import Agreement, Intervention, PartnerOrganization
from etools.applications.partners.prp_api import PRPAPI
from etools.applications.partners.serializers.prp_v1 import (
    PRPPartnerOrganizationWithStaffMembersSerializer,
    PRPSyncUserSerializer,
)
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
from etools.applications.reports.models import CountryProgramme
from etools.applications.users.models import Country, Realm, User
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
    # we should try all interventions except the ones in terminal statuses
    possible_interventions = Intervention.objects.exclude(status__in=[
        Intervention.DRAFT, Intervention.TERMINATED, Intervention.CLOSED, Intervention.SUSPENDED
    ]).order_by('id')
    processed = 0
    for intervention in possible_interventions:
        old_status = intervention.status
        with transaction.atomic():
            validator = InterventionValid(intervention, user=admin_user, disable_rigid_check=True)
            if validator.is_valid:
                if intervention.status != old_status:
                    intervention.save()
                    transaction.on_commit(lambda: send_pd_to_vision.delay(country_name, intervention.pk))
                    processed += 1
            else:
                bad_interventions.append(intervention)

    logger.error('Bad interventions {}'.format(len(bad_interventions)))
    logger.error('Bad interventions ids: ' + ' '.join(str(a.id) for a in bad_interventions))
    logger.info('Total interventions {}'.format(possible_interventions.count()))
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
            agreement__partner=partner,
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

    partner = PartnerOrganization.objects.get(id=partner_id)
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


@app.task
def transfer_active_pds_to_new_cp():
    today = timezone.now().date()

    original_tenant = connection.tenant
    try:
        for country in Country.objects.exclude(name='Global'):
            connection.set_tenant(country)

            active_cp = CountryProgramme.objects.filter(invalid=False, to_date__gte=today).first()
            if not active_cp:
                continue

            # exclude by id because of m2m filter
            outdated_active_pds = Intervention.objects.filter(
                status__in=[
                    Intervention.DRAFT,
                    Intervention.REVIEW,
                    Intervention.SIGNATURE,
                    Intervention.SIGNED,
                    Intervention.ACTIVE,
                ],
                end__gte=today,
            ).exclude(
                pk__in=Intervention.objects.filter(
                    end__gte=today,
                    country_programmes__invalid=False,
                    country_programmes__to_date__gte=today,
                ).values_list('id', flat=True)
            ).prefetch_related(
                'agreement__partner'
            )

            for pd in outdated_active_pds:
                pd.country_programmes.add(active_cp)
    finally:
        connection.set_tenant(original_tenant)


@app.task
def sync_partner(vendor_number=None, country=None):
    from etools.applications.partners.synchronizers import PartnerSynchronizer
    try:
        valid_response, response = get_data_from_insight(
            'partners/?vendor={vendor_code}', {
                "vendor_code": vendor_number,
                "businessarea": country.business_area_code
            })

        if "ROWSET" not in response:
            logger.exception("{} sync failed: Invalid response".format(PartnerSynchronizer.__name__))
            return _('The vendor number could not be found in INSIGHT')

        partner_resp = response["ROWSET"]["ROW"]
        partner_sync = PartnerSynchronizer(business_area_code=country.business_area_code)
        if not partner_sync._filter_records([partner_resp]):
            raise VisionException(_('Partner skipped because one or more of the required fields are missing'))

        partner_sync._partner_save(partner_resp, full_sync=False)
    except VisionException as e:
        logger.exception("{} sync failed".format(PartnerSynchronizer.__name__))
        return str(e)
    else:
        logger.info('Partner {} synced successfully.'.format(vendor_number))


@app.task
def intervention_expired():
    for country in Country.objects.exclude(name='Global').all():
        connection.set_tenant(country)
        _set_intervention_expired(country.name)


def _set_intervention_expired(country_name):
    # Check and transition to 'Expired' any contingency PD that has not
    # been activated and the CP for which was created has now expired
    logger.info(
        'Starting intervention expirations for country {}'.format(
            country_name,
        ),
    )
    today = timezone.now().date()
    pd_qs = Intervention.objects.filter(
        contingency_pd=True,
        status__in=[
            Intervention.REVIEW,
            Intervention.SIGNATURE,
            Intervention.SIGNED,
        ],
        end__gte=today,
    ).exclude(
        pk__in=Intervention.objects.filter(
            contingency_pd=True,
            end__gte=today,
            country_programmes__invalid=False,
            country_programmes__to_date__gte=today,
        ).values_list('id', flat=True)
    )
    for pd in pd_qs:
        pd.status = Intervention.EXPIRED
        pd.save()


def get_pilot_numbers(country_name):
    logger.info(
        '... Starting epd numbers counting for {}'.format(
            country_name,
        ),
    )
    now = timezone.now()
    today = now.date()
    pd_qs = Intervention.objects.filter(
        date_sent_to_partner__isnull=False,
    ).prefetch_related("agreement__partner")
    record = []
    for pd in pd_qs:
        fp_users = [fp.user for fp in pd.partner_focal_points.all()]
        has_the_partner_logged_in = pd.partner_focal_points.filter(
            user__last_login__gt=timezone.make_aware(datetime.datetime(2021, 10, 15))
        ).exists()
        act_qs = Activity.objects.filter(target_object_id=pd.id,
                                         target_content_type=ContentType.objects.get_for_model(pd))
        partner_entered_data = act_qs.filter(by_user__in=fp_users).exists()
        date_sent = pd.date_sent_to_partner.strftime("%Y-%m-%d") if pd.date_sent_to_partner else None
        record.append([
            country_name,
            pd.number,
            pd.agreement.partner.name,
            date_sent,
            has_the_partner_logged_in,
            partner_entered_data,
            pd.unicef_accepted,
            pd.partner_accepted,
            "Unicef" if pd.unicef_court else "Partner",
            pd.status,
            today.strftime("%Y-%m-%d"),
            pd.get_frontend_object_url()
        ])
    return record


@app.task
def epd_pilot_tracking():
    # TODO: remove this before ePD merges into the main branch
    # temporary task to get some epd pilot numbers emailed
    import csv
    import io
    import os

    from post_office import mail
    recipients = os.environ.get("EPD_PILOT_RECIPIENTS", "").split(",")
    countries = os.environ.get("EPD_PILOT_SCHEMAS", "").split(",")
    my_file = io.StringIO()
    my_numbers = [["CO Name", "PD No", "IP", "Date Sent to IP", "IP Logged In", "IP Entered Data",
                  "Unicef Accepted", "Partner Accepted", "Editable By", "Status", "Date of export",
                   "PD URL"]]
    for country in Country.objects.filter(schema_name__in=countries).all():
        connection.set_tenant(country)
        my_numbers += get_pilot_numbers(country.name)
    csv_writer = csv.writer(my_file)
    for line in my_numbers:
        csv_writer.writerow(line)

    # taken from https://stackoverflow.com/questions/55889474/convert-io-stringio-to-io-bytesio/55961119#55961119
    class BytesIOWrapper(io.BufferedReader):
        """Wrap a buffered bytes stream over TextIOBase string stream."""
        def __init__(self, text_io_buffer, encoding=None, errors=None, **kwargs):
            super(BytesIOWrapper, self).__init__(text_io_buffer, **kwargs)
            self.encoding = encoding or text_io_buffer.encoding or 'utf-8'
            self.errors = errors or text_io_buffer.errors or 'strict'

        def _encoding_call(self, method_name, *args, **kwargs):
            raw_method = getattr(self.raw, method_name)
            val = raw_method(*args, **kwargs)
            return val.encode(self.encoding, errors=self.errors)

        def read(self, size=-1):
            return self._encoding_call('read', size)

        def read1(self, size=-1):
            return self._encoding_call('read1', size)

        def peek(self, size=-1):
            return self._encoding_call('peek', size)
    bio = BytesIOWrapper(my_file)
    mail.send(
        recipients, "etoolsunicef@gmail.com", subject="ePD Pilot Numbers",
        attachments={"epd_pilot_values.csv": bio},
        message="enjoy!"
    )


@app.task
def update_interventions_task_chain():
    # call two tasks above one after another to avoid problems with parallel execution
    # because both of them handle similar cases yet in different way
    transfer_active_pds_to_new_cp()
    intervention_expired()


@app.task
def send_pd_to_vision(tenant_name: str, intervention_pk: int, retry_counter=0):
    from etools.applications.partners.synchronizers import PDVisionUploader

    original_tenant = connection.tenant

    try:
        tenant = get_tenant_model().objects.get(name=tenant_name)
        connection.set_tenant(tenant)

        # get just basic information. in case validation fail it will save us many db queries
        intervention = Intervention.objects.get(pk=intervention_pk)
        logger.info(f'Starting {intervention} upload to vision')

        synchronizer = PDVisionUploader(intervention)
        if not synchronizer.is_valid():
            logger.info('Instance is not ready to be synchronized')
            return

        # reload intervention with prefetched relations for serialization
        synchronizer.instance = Intervention.objects.detail_qs().get(pk=intervention_pk)
        response = synchronizer.sync()
        if response is None:
            logger.warning('Synchronizer internal check failed')
            return

        status_code, _data = response
        if status_code in [200, 201]:
            logger.info('Completed pd synchronization')
            return

        if retry_counter < 2:
            logger.info(f'Received {status_code} from vision synchronizer. retrying')
            send_pd_to_vision.apply_async(
                (tenant.name, intervention_pk,),
                {'retry_counter': retry_counter + 1},
                eta=timezone.now() + datetime.timedelta(minutes=1 + retry_counter)
            )
        else:
            logger.exception(f'Received {status_code} from vision synchronizer after 3 attempts. '
                             f'PD number: {intervention_pk}. Business area code: {tenant.business_area_code}')
    finally:
        connection.set_tenant(original_tenant)


@app.task
def sync_realms_to_prp(user_pk, last_modified_at_timestamp, retry_counter=0):
    last_modified_instance = Realm.objects.filter(user_id=user_pk).order_by('modified').last()
    if last_modified_instance and last_modified_instance.modified.timestamp() > last_modified_at_timestamp:
        # there were updates to user realms. skip
        return

    user = User.objects.filter(pk=user_pk).prefetch_related(
        Prefetch('realms', Realm.objects.filter(is_active=True).select_related('country', 'organization', 'group')),
    ).get()
    data = PRPSyncUserSerializer(instance=user).data

    try:
        PRPAPI().send_user_realms(data)
    except HTTPError as ex:
        if retry_counter < 2:
            logger.info(f'Received {ex} from prp api. retrying')
            sync_realms_to_prp.apply_async(
                (user_pk, last_modified_at_timestamp),
                {'retry_counter': retry_counter + 1},
                eta=timezone.now() + datetime.timedelta(minutes=1 + retry_counter)
            )
        else:
            logger.exception(f'Received {ex} from prp api while trying to send realms after 3 attempts. '
                             f'User pk: {user_pk}.')
