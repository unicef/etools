import datetime
import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.timezone import make_aware, now

from etools.applications.attachments.models import Attachment, FileType
from etools.applications.partners.models import (Agreement, AgreementAmendment, Assessment, Intervention,
                                                 InterventionAmendment, InterventionAttachment, PartnerOrganization,)
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
