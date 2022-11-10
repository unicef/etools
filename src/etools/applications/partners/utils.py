import datetime
import html
import logging
import typing

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import F, Q
from django.urls import reverse
from django.utils.timezone import make_aware, now

from dateutil.relativedelta import relativedelta
from unicef_attachments.models import Attachment, FileType

from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.partners.models import (
    Agreement,
    AgreementAmendment,
    Assessment,
    CoreValuesAssessment,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    PartnerOrganization,
    PartnerStaffMember,
)
from etools.applications.partners.prp_api import PRPPartnerUserResponse
from etools.applications.reports.models import CountryProgramme
from etools.applications.t2f.models import TravelAttachment
from etools.applications.users.models import Realm, User
from etools.libraries.tenant_support.utils import run_on_all_tenants

logger = logging.getLogger(__name__)


def update_or_create_attachment(
        code,
        file_type,
        content_type,
        object_id,
        filename,
):
    logger.info("code: {}".format(code))
    logger.info("content type: {}".format(content_type))
    logger.info("object_id: {}".format(object_id))
    try:
        Attachment.objects.update_or_create(
            code=code,
            content_type=content_type,
            object_id=object_id,
            defaults={
                "file": filename,
                "file_type": file_type,
            }
        )
    except Attachment.MultipleObjectsReturned:
        # If there are multiple objects already, this indicates
        # that the records exist, so things are ok.
        pass


def get_from_datetime(**kwargs):
    """Return from datetime to use

    If `all` provided, ignore and process since beginning of time,
    Otherwise process days and hours accordingly
    """
    if kwargs.get("all"):
        return make_aware(datetime.datetime(1970, 1, 1))

    # Start with midnight this morning, timezone-aware
    from_datetime = make_aware(datetime.datetime.combine(now(), datetime.time.min))

    # Adjust per the arguments
    if kwargs.get("days"):
        from_datetime = from_datetime - datetime.timedelta(days=kwargs.get("days"))

    if kwargs.get("hours"):
        from_datetime = from_datetime - datetime.timedelta(hours=kwargs.get("hours"))

    return from_datetime


def copy_attached_agreements(**kwargs):
    # Copy attached_agreement field content to
    # attachments model
    code = "partners_agreement"
    file_type, _ = FileType.objects.get_or_create(
        code=code,
        defaults={
            "label": "Signed Agreement",
            "name": "attached_agreement",
            "order": 0,
        }
    )
    if not file_type.group:
        file_type.group = []
    file_type.group.append(code)
    file_type.save(update_fields=['group'])

    content_type = ContentType.objects.get_for_model(Agreement)

    for agreement in Agreement.view_objects.filter(
            attached_agreement__isnull=False,
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        update_or_create_attachment(
            code,
            file_type,
            content_type,
            agreement.pk,
            agreement.attached_agreement,
        )


def copy_core_values_assessments(**kwargs):
    # Copy core_values_assessment field content to
    # attachments model
    code = "partners_partner_assessment"
    file_type, _ = FileType.objects.get_or_create(
        code=code,
        defaults={
            "label": "Core Values Assessment",
            "name": "core_values_assessment",
            "order": 0,
        }
    )
    if not file_type.group:
        file_type.group = []
    file_type.group.append(code)
    file_type.save(update_fields=['group'])

    content_type = ContentType.objects.get_for_model(CoreValuesAssessment)

    for core_values_assessment in CoreValuesAssessment.objects.filter(
            assessment__isnull=False,
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        update_or_create_attachment(
            code,
            file_type,
            content_type,
            core_values_assessment.pk,
            core_values_assessment.assessment,
        )


def copy_reports(**kwargs):
    # Copy report field content to attachments model
    code = "partners_assessment_report"
    file_type, _ = FileType.objects.get_or_create(
        code=code,
        defaults={
            "label": "Assessment Report",
            "name": "assessment_report",
            "order": 0,
        }
    )
    if not file_type.group:
        file_type.group = []
    file_type.group.append(code)
    file_type.save(update_fields=['group'])

    content_type = ContentType.objects.get_for_model(Assessment)

    for assessment in Assessment.objects.filter(
            report__isnull=False,
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        update_or_create_attachment(
            code,
            file_type,
            content_type,
            assessment.pk,
            assessment.report,
        )


def copy_signed_amendments(**kwargs):
    # Copy signed amendment field content to attachments model
    code = "partners_agreement_amendment"
    file_type, _ = FileType.objects.get_or_create(
        code=code,
        defaults={
            "label": "Agreement Amendment",
            "name": "agreement_signed_amendment",
            "order": 0,
        }
    )
    if not file_type.group:
        file_type.group = []
    file_type.group.append(code)
    file_type.save(update_fields=['group'])

    content_type = ContentType.objects.get_for_model(AgreementAmendment)

    for amendment in AgreementAmendment.view_objects.filter(
            signed_amendment__isnull=False,
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        update_or_create_attachment(
            code,
            file_type,
            content_type,
            amendment.pk,
            amendment.signed_amendment,
        )


def copy_interventions(**kwargs):
    # Copy prc review and signed pd field content to attachments model
    prc_code = "partners_intervention_prc_review"
    prc_file_type, _ = FileType.objects.get_or_create(
        code=prc_code,
        defaults={
            "label": "PRC Review",
            "name": "intervention_prc_review",
            "order": 0,
        }
    )
    if not prc_file_type.group:
        prc_file_type.group = []
    prc_file_type.group.append(prc_code)
    prc_file_type.save(update_fields=['group'])

    pd_code = "partners_intervention_signed_pd"
    pd_file_type, _ = FileType.objects.get_or_create(
        code=pd_code,
        defaults={
            "label": "Signed PD/SPD",
            "name": "intervention_signed_pd",
            "order": 0,
        }
    )
    if not pd_file_type.group:
        pd_file_type.group = []
    pd_file_type.group.append(prc_code)
    pd_file_type.save(update_fields=['group'])
    activation_letter_code = "partners_intervention_activation_letter"
    activation_letter, _ = FileType.objects.get_or_create(
        code=activation_letter_code,
        defaults={
            "label": "PD Activation Letter",
            "name": "activation_letter",
            "order": 0,
        }
    )
    if not activation_letter.group:
        activation_letter.group = []
    activation_letter.group.append(activation_letter_code)
    activation_letter.save(update_fields=['group'])

    termination_doc_code = "partners_intervention_termination_doc"
    termination_doc, _ = FileType.objects.get_or_create(
        code=termination_doc_code,
        defaults={
            "label": "PD Termination Document",
            "name": "termination_doc",
            "order": 0,
        }
    )
    if not termination_doc.group:
        termination_doc.group = []
    termination_doc.group.append(termination_doc_code)
    termination_doc.save(update_fields=['group'])

    content_type = ContentType.objects.get_for_model(Intervention)

    for intervention in Intervention.objects.filter(
            Q(prc_review_document__isnull=False) |
            Q(activation_letter__isnull=False) |
            Q(termination_doc__isnull=False) |
            Q(signed_pd_document__isnull=False),
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        if intervention.prc_review_document:
            update_or_create_attachment(
                prc_code,
                prc_file_type,
                content_type,
                intervention.pk,
                intervention.prc_review_document,
            )
        if intervention.signed_pd_document:
            update_or_create_attachment(
                pd_code,
                pd_file_type,
                content_type,
                intervention.pk,
                intervention.signed_pd_document,
            )
        if intervention.activation_letter:
            update_or_create_attachment(
                activation_letter_code,
                activation_letter,
                content_type,
                intervention.pk,
                intervention.activation_letter_attachment,
            )
        if intervention.termination_doc:
            update_or_create_attachment(
                termination_doc_code,
                termination_doc,
                content_type,
                intervention.pk,
                intervention.termination_doc_attachment,
            )


def copy_intervention_amendments(**kwargs):
    # Copy signed amendment field content to attachments model
    code = "partners_intervention_amendment_signed"
    file_type, _ = FileType.objects.get_or_create(
        code=code,
        defaults={
            "label": "PD/SPD Amendment",
            "name": "intervention_amendment_signed",
            "order": 0,
        }
    )
    if not file_type.group:
        file_type.group = []
    file_type.group.append(code)
    file_type.save(update_fields=['group'])

    content_type = ContentType.objects.get_for_model(InterventionAmendment)

    for amendment in InterventionAmendment.objects.filter(
            signed_amendment__isnull=False,
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        if amendment.signed_amendment:
            update_or_create_attachment(
                code,
                file_type,
                content_type,
                amendment.pk,
                amendment.signed_amendment,
            )


def copy_intervention_attachments(**kwargs):
    # Copy attachment field content to attachments model
    code = "partners_intervention_attachment"
    file_type, _ = FileType.objects.get_or_create(
        code=code,
        defaults={
            "label": "Intervention Attachment",
            "name": "intervention_attachment",
            "order": 0,
        }
    )
    if not file_type.group:
        file_type.group = []
    file_type.group.append(code)
    file_type.save(update_fields=['group'])

    content_type = ContentType.objects.get_for_model(InterventionAttachment)

    for attachment in InterventionAttachment.objects.filter(
            attachment__isnull=False,
            modified__gte=get_from_datetime(**kwargs)
    ).all():
        if attachment.attachment:
            update_or_create_attachment(
                code,
                file_type,
                content_type,
                attachment.pk,
                attachment.attachment,
            )


def copy_t2f_travel_attachments(**kwargs):
    # Copy t2f_travel_attachment field content to
    # attachments model
    code = "t2f_travel_attachment"
    file_type, _ = FileType.objects.get_or_create(
        code=code,
        defaults={
            "label": "Travel Attachment",
            "name": "t2f_travel_attachment",
            "order": 0,
        }
    )
    if not file_type.group:
        file_type.group = []
    file_type.group.append(code)
    file_type.save(update_fields=['group'])

    content_type = ContentType.objects.get_for_model(TravelAttachment)

    for t2f_travel_attachment in TravelAttachment.objects.filter(
            file__isnull=False,
    ).all():
        update_or_create_attachment(
            code,
            file_type,
            content_type,
            t2f_travel_attachment.pk,
            t2f_travel_attachment.file,
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
        copy_t2f_travel_attachments,
    ]
    for cmd in copy_commands:
        run_on_all_tenants(cmd, **kwargs)


def send_pca_required_notifications():
    """If the PD has an end date that is after the CP to date
    and the it is 30 days prior to the end of the CP,
    send a PCA required notification.
    """
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
        send_notification_with_template(
            recipients=recipients,
            template_name='partners/intervention/new_pca_required',
            context=context
        )


def send_pca_missing_notifications():
    """If the PD has en end date that is after PCA end date
    and the PD start date is in the previous CP cycle,
    and the current CP cycle has no PCA
    send a missing PCA notification.
    """
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
            send_notification_with_template(
                recipients=recipients,
                template_name='partners/intervention/pca_missing',
                context=context
            )


def send_agreement_suspended_notification(agreement, user):
    # send notification to user performing this action
    pd_list = []
    for intervention in agreement.interventions.all():
        sections = ", ".join(
            [str(s) for s in intervention.sections.all()]
        )
        url = "{}{}".format(settings.HOST, intervention.get_object_url())
        pd_list.append((sections, intervention.reference_number, url))

    send_notification_with_template(
        recipients=[user.email],  # person that initiated this update
        template_name="partners/agreement/suspended",
        context={
            "vendor_number": agreement.reference_number,
            "vendor_name": agreement.partner.name,
            "pd_list": pd_list,  # section, pd_number, link
        }
    )


def send_intervention_draft_notification():
    """Send an email to PD/SPD's focal point(s) if in draft status"""
    sdate_diff = make_aware(datetime.datetime.combine(now(), datetime.time.min) - datetime.timedelta(days=7))
    for intervention in Intervention.objects.filter(
            status=Intervention.DRAFT,
            created__lt=sdate_diff,
    ):
        recipients = [
            u.user.email for u in intervention.unicef_focal_points.all()
            if u.user.email
        ]
        send_notification_with_template(
            recipients=recipients,
            template_name="partners/intervention/draft",
            context={
                "reference_number": intervention.reference_number,
                "title": intervention.title,
            }
        )


def send_intervention_past_start_notification():
    """Send an email to PD/SPD's focal point(s) if signed
    and start date is past with no FR added"""
    intervention_qs = Intervention.objects.filter(
        status=Intervention.SIGNED,
        start__lt=datetime.date.today(),
        frs__isnull=False,
    )
    for intervention in intervention_qs.all():
        recipients = [
            u.user.email for u in intervention.unicef_focal_points.all()
            if u.user.email
        ]
        send_notification_with_template(
            recipients=recipients,
            template_name="partners/intervention/past-start",
            context={
                "reference_number": intervention.reference_number,
                "title": intervention.title,
                "url": "{}pmp/interventions/{}/details".format(
                    settings.HOST,
                    intervention.pk,
                )
            }
        )


def send_intervention_amendment_added_notification(intervention):
    """Send an email to PD/SPD's focal point(s) if intervention amendment is added"""
    recipients = [
        fp.email for fp in intervention.partner_focal_points.all()
        if fp.email
    ]
    amendment_choices = InterventionAmendment.AMENDMENT_TYPES + InterventionAmendment.AMENDMENT_TYPES_OLD
    amendment_choice_values = [html.escape(amendment_choices[t])
                               for t in intervention.amendments.order_by('id').last().types]

    send_notification_with_template(
        recipients=recipients,
        template_name="partners/intervention/amendment/added",
        context={
            "title": intervention.title,
            "reference_number": intervention.reference_number,
            "amendment_type": ', '.join(amendment_choice_values),
        }
    )


def sync_partner_staff_member(partner: PartnerOrganization, staff_member_data: PRPPartnerUserResponse):
    user_update_fields = {
        'is_active': staff_member_data.is_active,
        'first_name': staff_member_data.first_name, 'last_name': staff_member_data.last_name,
    }
    user, user_created = User.objects.get_or_create(email__iexact=staff_member_data.email, defaults={
        'email': staff_member_data.email, 'username': staff_member_data.email,
        **user_update_fields
    })
    if not user_created:
        for key, value in user_update_fields.items():
            setattr(user, key, value)
        user.save()

    profile = user.profile
    profile.job_title = staff_member_data.title
    profile.phone_number = staff_member_data.phone_number
    profile.country = profile.country or connection.tenant
    profile.save()
    Realm.objects.update_or_create(
        user=user,
        country=connection.tenant,
        organization=partner.organization,
        group=Group.objects.get_or_create(name='IP Viewer')[0],
        defaults={'is_active': user.is_active}
    )

    staff_member_update_fields = {
        'user': user,
        'title': staff_member_data.title, 'active': staff_member_data.is_active,
        'first_name': staff_member_data.first_name, 'last_name': staff_member_data.last_name,
        'phone': staff_member_data.phone_number,
    }
    staff_member, staff_member_created = PartnerStaffMember.objects.get_or_create(
        partner=partner, email__iexact=staff_member_data.email,
        defaults={
            'email': staff_member_data.email, 'partner': partner,
            **staff_member_update_fields
        }
    )
    if not staff_member_created:
        for key, value in staff_member_update_fields.items():
            setattr(staff_member, key, value)
        staff_member.save()


class Quarter(typing.NamedTuple):
    quarter: int
    start: datetime.date
    end: datetime.date


def get_quarters_range(start: datetime.date, end: datetime.date) -> typing.List[Quarter]:
    """first date included, last excluded for every period in range"""
    if not start or not end:
        return []

    quarters = []
    i = 0
    while start < end:
        quarter_end = start + relativedelta(months=3) - relativedelta(days=1)
        period_end = min(quarter_end, end)
        quarters.append(Quarter(i + 1, start, period_end))
        start = quarter_end + relativedelta(days=1)
        i += 1

    return quarters
