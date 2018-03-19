from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db.models import Q

from attachments.models import Attachment, FileType
from partners.models import (
    Agreement,
    AgreementAmendment,
    Assessment,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    PartnerOrganization,
)
from utils.common.utils import run_on_all_tenants

logger = logging.getLogger(__name__)


def copy_attached_agreements():
    # Copy attached_agreement field content to
    # attachments model
    file_type, _ = FileType.objects.get_or_create(
        code="partners_agreement",
        defaults={
            "label": "Attached Agreement",
            "name": "attached_agreement",
            "order": 0,
        }
    )

    content_type = ContentType.objects.get_for_model(Agreement)

    for agreement in Agreement.view_objects.filter(
        attached_agreement__isnull=False
    ).all():
        logger.info("code: {}".format(file_type.code))
        logger.info("content type: {}".format(content_type))
        logger.info("agreement: {}".format(agreement.pk))
        attachment, created = Attachment.objects.get_or_create(
            code=file_type.code,
            content_type=content_type,
            object_id=agreement.pk,
            file_type=file_type,
            defaults={"file": agreement.attached_agreement}
        )


def copy_core_values_assessments():
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
        core_values_assessment__isnull=False
    ).all():
        attachment, _ = Attachment.objects.get_or_create(
            content_type=content_type,
            object_id=partner.pk,
            file_type=file_type,
            code=file_type.code,
            defaults={"file": partner.core_values_assessment}
        )


def copy_reports():
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
        report__isnull=False
    ).all():
        attachment, _ = Attachment.objects.get_or_create(
            content_type=content_type,
            object_id=assessment.pk,
            file_type=file_type,
            code=file_type.code,
            defaults={"file": assessment.report}
        )


def copy_signed_amendments():
    # Copy signed amendment field content to attachments model
    file_type, _ = FileType.objects.get_or_create(
        code="partners_agreement_amendment",
        defaults={
            "label": "Agreement Signed Amendment",
            "name": "agreement_signed_amendment",
            "order": 0,
        }
    )

    content_type = ContentType.objects.get_for_model(AgreementAmendment)

    for amendment in AgreementAmendment.view_objects.filter(
        signed_amendment__isnull=False
    ).all():
        attachment, _ = Attachment.objects.get_or_create(
            content_type=content_type,
            object_id=amendment.pk,
            file_type=file_type,
            code=file_type.code,
            defaults={"file": amendment.signed_amendment}
        )


def copy_interventions():
    # Copy prc review and signed pd field content to attachments model
    prc_file_type, _ = FileType.objects.get_or_create(
        code="partners_intervention_prc_review",
        defaults={
            "label": "Intervention PRC Review",
            "name": "intervention_prc_review",
            "order": 0,
        }
    )
    pd_file_type, _ = FileType.objects.get_or_create(
        code="partners_intervention_signed_pd",
        defaults={
            "label": "Intervention Signed PD",
            "name": "intervention_signed_pd",
            "order": 0,
        }
    )

    content_type = ContentType.objects.get_for_model(Intervention)

    for intervention in Intervention.objects.filter(
            Q(prc_review_document__isnull=False) |
            Q(signed_pd_document__isnull=False)
    ).all():
        if intervention.prc_review_document:
            attachment, _ = Attachment.objects.get_or_create(
                content_type=content_type,
                object_id=intervention.pk,
                file_type=prc_file_type,
                code=prc_file_type.code,
                defaults={"file": intervention.prc_review_document}
            )
        if intervention.signed_pd_document:
            attachment, _ = Attachment.objects.get_or_create(
                content_type=content_type,
                object_id=intervention.pk,
                file_type=pd_file_type,
                code=pd_file_type.code,
                defaults={"file": intervention.signed_pd_document}
            )


def copy_intervention_amendments():
    # Copy signed amendment field content to attachments model
    file_type, _ = FileType.objects.get_or_create(
        code="partners_intervention_amendment_signed",
        defaults={
            "label": "Intervention Amendment Signed",
            "name": "intervention_amendment_signed",
            "order": 0,
        }
    )

    content_type = ContentType.objects.get_for_model(InterventionAmendment)

    for amendment in InterventionAmendment.objects.filter(
            signed_amendment__isnull=False
    ).all():
        if amendment.signed_amendment:
            attachment, _ = Attachment.objects.get_or_create(
                content_type=content_type,
                object_id=amendment.pk,
                file_type=file_type,
                code=file_type.code,
                defaults={"file": amendment.signed_amendment}
            )


def copy_intervention_attachments():
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
            attachment__isnull=False
    ).all():
        if attachment.attachment:
            a, _ = Attachment.objects.get_or_create(
                content_type=content_type,
                object_id=attachment.pk,
                file_type=file_type,
                code=file_type.code,
                defaults={"file": attachment.attachment}
            )


class Command(BaseCommand):
    def handle(self, *args, **options):
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
            run_on_all_tenants(cmd)
