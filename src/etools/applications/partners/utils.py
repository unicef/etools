import codecs
import csv
import datetime
import json
import logging
import requests

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models import F, Q
from django.urls import reverse
from django.utils.timezone import now, make_aware

from etools.applications.attachments.models import Attachment, FileType
from etools.applications.EquiTrack.utils import run_on_all_tenants
from etools.applications.notification.utils import send_notification_using_email_template
from etools.applications.reports.models import CountryProgramme

logger = logging.getLogger(__name__)


class Vividict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


class HashableDict(dict):
    def __hash__(self):
        return hash(frozenset(self.items()))


def get_data_from_insight(endpoint, data={}):
    url = '{}/{}'.format(
        settings.VISION_URL,
        endpoint
    ).format(**data)

    response = requests.get(
        url,
        headers={'Content-Type': 'application/json'},
        auth=(settings.VISION_USER, settings.VISION_PASSWORD),
        verify=False
    )
    if response.status_code != 200:
        return False, 'Loading data from Vision Failed, status {}'.format(response.status_code)
    try:
        result = json.loads(response.json())
    except ValueError:
        return False, 'Loading data from Vision Failed, no valid response returned for data: {}'.format(data)
    return True, result


def process_permissions(permission_dict):
    '''
    :param permission_dict: the csv field read as a dictionary where the header contains the following keys:
    'Group' - the Django Group the user should belong to - field may be blank.
    'Condition' - the condition that should be required to satisfy.
    'Status' - the status of the model (represents state)
    'Field' - the field we are targetting (eg: start_date) this needs to be spelled exactly as it is on the model
    'Action' - One of the following values: 'view', 'edit', 'required'
    'Allowed' - the boolean 'TRUE' or 'FALSE' if the action should be allowed if the: group match, stastus match and
    condition match are all valid

    *** note that in order for the system to know what the default behaviour should be on a specified field for a
    specific action, only the conditions opposite to the default should be defined.

    :return:
     a nested dictionary where the first key is the field targeted, the following nested key is the action possible,
     and the last nested key is the action parameter
     eg:
     {'start_date': {'edit': {'false': [{'condition': 'condition2',
                                         'group': 'UNICEF USER',
                                         'status': 'Active'}]},
                     'required': {'true': [{'condition': '',
                                            'group': 'UNICEF USER',
                                            'status': 'Active'},
                                           {'condition': '',
                                            'group': 'UNICEF USER',
                                            'status': 'Signed'}]},
                     'view': {'true': [{'condition': 'condition1',
                                        'group': 'PM',
                                        'status': 'Active'}]}}}
    '''

    result = Vividict()
    possible_actions = ['edit', 'required', 'view']

    for row in permission_dict:
        field = row['Field Name']
        action = row['Action'].lower()
        allowed = row['Allowed'].lower()
        assert action in possible_actions

        if isinstance(result[field][action][allowed], dict):
            result[field][action][allowed] = []

        # this action should not have been defined with any other allowed param
        assert list(result[field][action].keys()) == [allowed], \
            'There cannot be two types of "allowed" defined on the same '\
            'field with the same action as the system will not  be able' \
            ' to have a default behaviour.  field=%r, action=%r, allowed=%r' \
            % (field, action, allowed)

        result[field][action][allowed].append({
            'group': row['Group'],
            'condition': row['Condition'],
            'status': row['Status'].lower()
        })
    return result


def import_permissions(model_name):
    permission_file_map = {
        'Intervention': settings.PACKAGE_ROOT + '/assets/partner/intervention_permissions.csv',
        'Agreement': settings.PACKAGE_ROOT + '/assets/partner/agreement_permissions.csv'
    }

    def process_file():
        with codecs.open(permission_file_map[model_name], 'r', encoding="ascii") as csvfile:
            sheet = csv.DictReader(csvfile, delimiter=',', quotechar='|')
            result = process_permissions(sheet)
        return result

    cache_key = "public-{}-permissions".format(model_name.lower())
    response = cache.get_or_set(cache_key, process_file, 60 * 60 * 24)

    return response


def get_quarter(retrieve_date=None):
    if not retrieve_date:
        retrieve_date = datetime.datetime.today()
    month = retrieve_date.month
    if 0 < month <= 3:
        quarter = 'q1'
    elif 3 < month <= 6:
        quarter = 'q2'
    elif 6 < month <= 9:
        quarter = 'q3'
    else:
        quarter = 'q4'
    return quarter


def update_or_create_attachment(file_type, content_type, object_id, filename):
    logger.info("code: {}".format(file_type.code))
    logger.info("content type: {}".format(content_type))
    logger.info("object_id: {}".format(object_id))
    attachment, created = Attachment.objects.update_or_create(
        code=file_type.code,
        content_type=content_type,
        object_id=object_id,
        file_type=file_type,
        defaults={"file": filename}
    )


def get_from_datetime(**kwargs):
    """Return from datetime to use

    If `all` provided, ignore and process since beginning of time,
    Otherwise process days and hours accordingly
    """
    if kwargs.get("all"):
        return make_aware(datetime.datetime(1970, 1, 1))

    # Start with midnight this morning, timezone-aware
    from_datetime = now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Adjust per the arguments
    if kwargs.get("days"):
        from_datetime = from_datetime - datetime.timedelta(days=kwargs.get("days"))

    if kwargs.get("hours"):
        from_datetime = from_datetime - datetime.timedelta(hours=kwargs.get("hours"))

    return from_datetime


def copy_attached_agreements(**kwargs):
    # Copy attached_agreement field content to
    # attachments model
    from etools.applications.partners.models import Agreement

    file_type, _ = FileType.objects.get_or_create(
        code="partners_agreement",
        defaults={
            "label": "Signed Agreement",
            "name": "attached_agreement",
            "order": 0,
        }
    )

    content_type = ContentType.objects.get_for_model(Agreement)

    for agreement in Agreement.view_objects.filter(
            attached_agreement__isnull=False,
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        update_or_create_attachment(
            file_type,
            content_type,
            agreement.pk,
            agreement.attached_agreement,
        )


def copy_core_values_assessments(**kwargs):
    # Copy core_values_assessment field content to
    # attachments model
    from etools.applications.partners.models import PartnerOrganization

    file_type, _ = FileType.objects.get_or_create(
        code="partners_partner_assessment",
        defaults={
            "label": "Core Values Assessment",
            "name": "core_values_assessment",
            "order": 0,
        }
    )

    content_type = ContentType.objects.get_for_model(PartnerOrganization)

    for partner in PartnerOrganization.objects.filter(
            core_values_assessment__isnull=False,
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        update_or_create_attachment(
            file_type,
            content_type,
            partner.pk,
            partner.core_values_assessment,
        )


def copy_reports(**kwargs):
    # Copy report field content to attachments model
    from etools.applications.partners.models import Assessment

    file_type, _ = FileType.objects.get_or_create(
        code="partners_assessment_report",
        defaults={
            "label": "Assessment Report",
            "name": "assessment_report",
            "order": 0,
        }
    )

    content_type = ContentType.objects.get_for_model(Assessment)

    for assessment in Assessment.objects.filter(
            report__isnull=False,
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        update_or_create_attachment(
            file_type,
            content_type,
            assessment.pk,
            assessment.report,
        )


def copy_signed_amendments(**kwargs):
    # Copy signed amendment field content to attachments model
    from etools.applications.partners.models import AgreementAmendment

    file_type, _ = FileType.objects.get_or_create(
        code="partners_agreement_amendment",
        defaults={
            "label": "Agreement Amendment",
            "name": "agreement_signed_amendment",
            "order": 0,
        }
    )

    content_type = ContentType.objects.get_for_model(AgreementAmendment)

    for amendment in AgreementAmendment.view_objects.filter(
            signed_amendment__isnull=False,
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        update_or_create_attachment(
            file_type,
            content_type,
            amendment.pk,
            amendment.signed_amendment,
        )


def copy_interventions(**kwargs):
    # Copy prc review and signed pd field content to attachments model
    from etools.applications.partners.models import Intervention

    prc_file_type, _ = FileType.objects.get_or_create(
        code="partners_intervention_prc_review",
        defaults={
            "label": "PRC Review",
            "name": "intervention_prc_review",
            "order": 0,
        }
    )
    pd_file_type, _ = FileType.objects.get_or_create(
        code="partners_intervention_signed_pd",
        defaults={
            "label": "Signed PD/SSFA",
            "name": "intervention_signed_pd",
            "order": 0,
        }
    )

    content_type = ContentType.objects.get_for_model(Intervention)

    for intervention in Intervention.objects.filter(
            Q(prc_review_document__isnull=False) |
            Q(signed_pd_document__isnull=False),
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        if intervention.prc_review_document:
            update_or_create_attachment(
                prc_file_type,
                content_type,
                intervention.pk,
                intervention.prc_review_document,
            )
        if intervention.signed_pd_document:
            update_or_create_attachment(
                pd_file_type,
                content_type,
                intervention.pk,
                intervention.signed_pd_document,
            )


def copy_intervention_amendments(**kwargs):
    # Copy signed amendment field content to attachments model
    from etools.applications.partners.models import InterventionAmendment

    file_type, _ = FileType.objects.get_or_create(
        code="partners_intervention_amendment_signed",
        defaults={
            "label": "PD/SSFA Amendment",
            "name": "intervention_amendment_signed",
            "order": 0,
        }
    )

    content_type = ContentType.objects.get_for_model(InterventionAmendment)

    for amendment in InterventionAmendment.objects.filter(
            signed_amendment__isnull=False,
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        if amendment.signed_amendment:
            update_or_create_attachment(
                file_type,
                content_type,
                amendment.pk,
                amendment.signed_amendment,
            )


def copy_intervention_attachments(**kwargs):
    # Copy attachment field content to attachments model
    from etools.applications.partners.models import InterventionAttachment

    file_type, _ = FileType.objects.get_or_create(
        code="partners_intervention_attachment",
        defaults={
            "label": "Intervention Attachment",
            "name": "intervention_attachment",
            "order": 0,
        }
    )

    content_type = ContentType.objects.get_for_model(InterventionAttachment)

    for attachment in InterventionAttachment.objects.filter(
            attachment__isnull=False,
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        if attachment.attachment:
            update_or_create_attachment(
                file_type,
                content_type,
                attachment.pk,
                attachment.attachment,
            )


def copy_all_attachments(**kwargs):
    copy_commands = [
        copy_attached_agreements,
        copy_core_values_assessments,
        copy_reports,
        copy_signed_amendments,
        copy_interventions,
        copy_intervention_amendments,
        copy_intervention_attachments,
    ]
    for cmd in copy_commands:
        run_on_all_tenants(cmd, **kwargs)


def send_pca_required_notifications():
    """If the PD has an end date that is after the CP to date
    and the it is 30 days prior to the end of the CP,
    send a PCA required notification.
    """
    from etools.applications.partners.models import Intervention

    days_lead = datetime.date.today() + datetime.timedelta(
        days=settings.PCA_REQUIRED_NOTIFICATION_LEAD
    )
    pd_list = set()
    for cp in CountryProgramme.objects.filter(to_date=days_lead):
        # For PDs related directly to CP
        for pd in cp.interventions.filter(
                document_type=Intervention.PD,
                end__gt=cp.to_date
        ):
            pd_list.add(pd)

        # For PDs by way of agreement
        for agreement in cp.agreements.filter(interventions__end__gt=cp.to_date):
            for pd in agreement.interventions.filter(
                    document_type=Intervention.PD,
                    end__gt=cp.to_date
            ):
                pd_list.add(pd)

    for pd in pd_list:
        recipients = [u.user.email for u in pd.unicef_focal_points.all()]
        context = {
            "reference_number": pd.reference_number,
            "partner_name": str(pd.agreement.partner),
            "pd_link": reverse(
                "partners_api:intervention-detail",
                args=[pd.pk]
            ),
        }
        send_notification_using_email_template(
            recipients=recipients,
            email_template_name='partners/intervention/new_pca_required',
            context=context
        )


def send_pca_missing_notifications():
    """If the PD has en end date that is after PCA end date
    and the PD start date is in the previous CP cycle,
    and the current CP cycle has no PCA
    send a missing PCA notification.
    """
    from etools.applications.partners.models import Agreement, Intervention

    # get PDs that have end date after PCA end date
    # this means that the CP is in previous cycle
    # (as PCA and CP end dates are always equal)
    # and PD start date in the previous CP cycle
    intervention_qs = Intervention.objects.filter(
        document_type=Intervention.PD,
        agreement__agreement_type=Agreement.PCA,
        agreement__country_programme__from_date__lt=F("start"),
        end__gt=F("agreement__end")
    )
    for pd in intervention_qs:
        # check that partner has no PCA in the current CP cycle
        cp_previous = pd.agreement.country_programme
        pca_next_qs = Agreement.objects.filter(
            partner=pd.agreement.partner,
            country_programme__from_date__gt=cp_previous.to_date
        )
        if not pca_next_qs.exists():
            recipients = [u.user.email for u in pd.unicef_focal_points.all()]
            context = {
                "reference_number": pd.reference_number,
                "partner_name": str(pd.agreement.partner),
                "pd_link": reverse(
                    "partners_api:intervention-detail",
                    args=[pd.pk]
                ),
            }
            send_notification_using_email_template(
                recipients=recipients,
                email_template_name='partners/intervention/pca_missing',
                context=context
            )
