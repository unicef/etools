import datetime
import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Q
from django.urls import reverse
from django.utils.timezone import make_aware, now

from unicef_notification.utils import send_notification_with_template

from etools.applications.attachments.models import Attachment, FileType
from etools.applications.partners.models import (
    Agreement,
    AgreementAmendment,
    Assessment,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    PartnerOrganization,
)
from etools.applications.reports.models import CountryProgramme
from etools.applications.utils.common.utils import run_on_all_tenants

logger = logging.getLogger(__name__)


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
