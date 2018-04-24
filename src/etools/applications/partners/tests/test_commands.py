
from django.core.management import call_command

from etools.applications.attachments.models import Attachment
from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import (AgreementAmendmentFactory, AgreementFactory,
                                                          AssessmentFactory, InterventionAmendmentFactory,
                                                          InterventionAttachmentFactory,
                                                          InterventionFactory, PartnerFactory,)


class TestCopyAttachments(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.file_type_partner = AttachmentFileTypeFactory(
            code="partners_partner_assessment"
        )
        cls.file_type_agreement = AttachmentFileTypeFactory(
            code="partners_agreement"
        )
        cls.file_type_assessment = AttachmentFileTypeFactory(
            code="partners_assessment_report"
        )
        cls.file_type_agreement_amendment = AttachmentFileTypeFactory(
            code="partners_agreement_amendment"
        )
        cls.file_type_intervention_prc_review = AttachmentFileTypeFactory(
            code="partners_intervention_prc_review"
        )
        cls.file_type_intervention_signed_pd = AttachmentFileTypeFactory(
            code="partners_intervention_signed_pd"
        )
        cls.file_type_intervention_amendment = AttachmentFileTypeFactory(
            code="partners_intervention_amendment_signed"
        )
        cls.file_type_intervention_attachment = AttachmentFileTypeFactory(
            code="partners_intervention_attachment"
        )
        cls.partner = PartnerFactory(
            core_values_assessment="sample.pdf"
        )
        cls.agreement = AgreementFactory(
            attached_agreement="sample.pdf"
        )
        cls.assessment = AssessmentFactory(
            report="sample.pdf"
        )
        cls.agreement_amendment = AgreementAmendmentFactory(
            signed_amendment="sample.pdf"
        )
        cls.intervention = InterventionFactory(
            prc_review_document="prc_sample.pdf",
            signed_pd_document="pd_sample.pdf"
        )
        cls.intervention_amendment = InterventionAmendmentFactory(
            signed_amendment="sample.pdf"
        )
        cls.intervention_attachment = InterventionAttachmentFactory(
            attachment="sample.pdf"
        )

    def test_partner_create(self):
        attachment_qs = Attachment.objects.filter(
            object_id=self.partner.pk,
            code=self.file_type_partner.code,
            file_type=self.file_type_partner
        )
        self.assertFalse(attachment_qs.exists())
        call_command("copy_attachments")
        self.assertTrue(attachment_qs.exists())
        attachment = attachment_qs.last()
        self.assertEqual(
            attachment.file.name,
            self.partner.core_values_assessment.name
        )

    def test_partner_update(self):
        attachment = AttachmentFactory(
            content_object=self.partner,
            file_type=self.file_type_partner,
            code=self.file_type_partner.code,
            file="random.pdf"
        )
        call_command("copy_attachments")
        attachment_update = Attachment.objects.get(pk=attachment.pk)
        self.assertEqual(
            attachment_update.file.name,
            self.partner.core_values_assessment.name
        )

    def test_agreement_create(self):
        attachment_qs = Attachment.objects.filter(
            object_id=self.agreement.pk,
            code=self.file_type_agreement.code,
            file_type=self.file_type_agreement
        )
        self.assertFalse(attachment_qs.exists())
        call_command("copy_attachments")
        self.assertTrue(attachment_qs.exists())
        attachment = attachment_qs.last()
        self.assertEqual(
            attachment.file.name,
            self.agreement.attached_agreement.name
        )

    def test_agreement_update(self):
        attachment = AttachmentFactory(
            content_object=self.agreement,
            file_type=self.file_type_agreement,
            code=self.file_type_agreement.code,
            file="random.pdf"
        )
        call_command("copy_attachments")
        attachment_update = Attachment.objects.get(pk=attachment.pk)
        self.assertEqual(
            attachment_update.file.name,
            self.agreement.attached_agreement.name
        )

    def test_assessment_create(self):
        attachment_qs = Attachment.objects.filter(
            object_id=self.assessment.pk,
            code=self.file_type_assessment.code,
            file_type=self.file_type_assessment
        )
        self.assertFalse(attachment_qs.exists())
        call_command("copy_attachments")
        self.assertTrue(attachment_qs.exists())
        attachment = attachment_qs.last()
        self.assertEqual(
            attachment.file.name,
            self.assessment.report.name
        )

    def test_assessment_update(self):
        attachment = AttachmentFactory(
            content_object=self.assessment,
            file_type=self.file_type_assessment,
            code=self.file_type_assessment.code,
            file="random.pdf"
        )
        call_command("copy_attachments")
        attachment_update = Attachment.objects.get(pk=attachment.pk)
        self.assertEqual(
            attachment_update.file.name,
            self.assessment.report.name
        )

    def test_agreement_amendment_create(self):
        attachment_qs = Attachment.objects.filter(
            object_id=self.agreement_amendment.pk,
            code=self.file_type_agreement_amendment.code,
            file_type=self.file_type_agreement_amendment
        )
        self.assertFalse(attachment_qs.exists())
        call_command("copy_attachments")
        self.assertTrue(attachment_qs.exists())
        attachment = attachment_qs.last()
        self.assertEqual(
            attachment.file.name,
            self.agreement_amendment.signed_amendment.name
        )

    def test_agreement_amendment_update(self):
        attachment = AttachmentFactory(
            content_object=self.agreement_amendment,
            file_type=self.file_type_agreement_amendment,
            code=self.file_type_agreement_amendment.code,
            file="random.pdf"
        )
        call_command("copy_attachments")
        attachment_update = Attachment.objects.get(pk=attachment.pk)
        self.assertEqual(
            attachment_update.file.name,
            self.agreement_amendment.signed_amendment.name
        )

    def test_intervention_create(self):
        attachment_prc_qs = Attachment.objects.filter(
            object_id=self.intervention.pk,
            code=self.file_type_intervention_prc_review.code,
            file_type=self.file_type_intervention_prc_review
        )
        attachment_pd_qs = Attachment.objects.filter(
            object_id=self.intervention.pk,
            code=self.file_type_intervention_signed_pd.code,
            file_type=self.file_type_intervention_signed_pd
        )
        self.assertFalse(attachment_prc_qs.exists())
        self.assertFalse(attachment_pd_qs.exists())
        call_command("copy_attachments")
        self.assertTrue(attachment_prc_qs.exists())
        self.assertTrue(attachment_pd_qs.exists())
        attachment_prc = attachment_prc_qs.last()
        self.assertEqual(
            attachment_prc.file.name,
            self.intervention.prc_review_document.name
        )
        attachment_pd = attachment_pd_qs.last()
        self.assertEqual(
            attachment_pd.file.name,
            self.intervention.signed_pd_document.name
        )

    def test_intervention_update(self):
        attachment_prc = AttachmentFactory(
            content_object=self.intervention,
            file_type=self.file_type_intervention_prc_review,
            code=self.file_type_intervention_prc_review.code,
            file="random.pdf"
        )
        attachment_pd = AttachmentFactory(
            content_object=self.intervention,
            file_type=self.file_type_intervention_signed_pd,
            code=self.file_type_intervention_signed_pd.code,
            file="random.pdf"
        )
        call_command("copy_attachments")
        attachment_prc_update = Attachment.objects.get(pk=attachment_prc.pk)
        self.assertEqual(
            attachment_prc_update.file.name,
            self.intervention.prc_review_document.name
        )
        attachment_pd_update = Attachment.objects.get(pk=attachment_pd.pk)
        self.assertEqual(
            attachment_pd_update.file.name,
            self.intervention.signed_pd_document.name
        )

    def test_intervention_amendment_create(self):
        attachment_qs = Attachment.objects.filter(
            object_id=self.intervention_amendment.pk,
            code=self.file_type_intervention_amendment.code,
            file_type=self.file_type_intervention_amendment
        )
        self.assertFalse(attachment_qs.exists())
        call_command("copy_attachments")
        self.assertTrue(attachment_qs.exists())
        attachment = attachment_qs.last()
        self.assertEqual(
            attachment.file.name,
            self.intervention_amendment.signed_amendment.name
        )

    def test_intervention_amendment_update(self):
        attachment = AttachmentFactory(
            content_object=self.intervention_amendment,
            file_type=self.file_type_intervention_amendment,
            code=self.file_type_intervention_amendment.code,
            file="random.pdf"
        )
        call_command("copy_attachments")
        attachment_update = Attachment.objects.get(pk=attachment.pk)
        self.assertEqual(
            attachment_update.file.name,
            self.intervention_amendment.signed_amendment.name
        )

    def test_intervention_attachment_create(self):
        attachment_qs = Attachment.objects.filter(
            object_id=self.intervention_attachment.pk,
            code=self.file_type_intervention_attachment.code,
            file_type=self.file_type_intervention_attachment
        )
        self.assertFalse(attachment_qs.exists())
        call_command("copy_attachments")
        self.assertTrue(attachment_qs.exists())
        attachment = attachment_qs.last()
        self.assertEqual(
            attachment.file.name,
            self.intervention_attachment.attachment.name
        )

    def test_intervention_attachment_update(self):
        attachment = AttachmentFactory(
            content_object=self.intervention_attachment,
            file_type=self.file_type_intervention_attachment,
            code=self.file_type_intervention_attachment.code,
            file="random.pdf"
        )
        call_command("copy_attachments")
        attachment_update = Attachment.objects.get(pk=attachment.pk)
        self.assertEqual(
            attachment_update.file.name,
            self.intervention_attachment.attachment.name
        )
