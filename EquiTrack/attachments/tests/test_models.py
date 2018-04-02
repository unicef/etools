from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.utils import six

from attachments import models
from attachments.tests.factories import (
    AttachmentFactory,
    AttachmentFileTypeFactory,
)
from EquiTrack.tests.cases import BaseTenantTestCase
from partners import models as partner_models
from partners.tests.factories import (
    AgreementAmendmentFactory,
    AgreementFactory,
    AssessmentFactory,
    InterventionAmendmentFactory,
    InterventionAttachmentFactory,
    InterventionFactory,
    PartnerFactory,
)


class TestGenerateFilePath(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory()
        cls.agreement = AgreementFactory(partner=cls.partner)
        cls.intervention = InterventionFactory(agreement=cls.agreement)

    def assert_file_path(self, file_path, file_path_list, path_type=None):
        if path_type == "partners":
            file_path_list = [
                connection.schema_name,
                "file_attachments",
                "partner_organization",
                str(self.partner.pk),
            ] + file_path_list
        elif path_type == "agreementamendment":
            file_path_list = [
                connection.schema_name,
                "file_attachments",
                "partner_org",
            ] + file_path_list
        self.assertEqual(file_path, "/".join(file_path_list))

    def test_agreement(self):
        attachment = AttachmentFactory(content_object=self.agreement)
        file_path = models.generate_file_path(attachment, "test.pdf")
        self.assert_file_path(file_path, [
            "agreements",
            self.agreement.agreement_number.strip("/"),
            "test.pdf"
        ], "partners")
        # check against old file path function
        # except new paths do not have '//'
        file_path_old = partner_models.get_agreement_path(
            self.agreement,
            "test.pdf"
        )
        self.assertEqual(file_path, file_path_old.replace("//", "/"))

    def test_assessment(self):
        assessment = AssessmentFactory(partner=self.partner)
        attachment = AttachmentFactory(content_object=assessment)
        file_path = models.generate_file_path(attachment, "test.pdf")
        self.assert_file_path(file_path, [
            "assesments",
            str(assessment.pk),
            "test.pdf"
        ], "partners")
        # check against old file path function
        file_path_old = partner_models.get_assesment_path(
            assessment,
            "test.pdf"
        )
        self.assertEqual(file_path, file_path_old)

    def test_intervention_amendment(self):
        amendment = InterventionAmendmentFactory(
            intervention=self.intervention
        )
        attachment = AttachmentFactory(content_object=amendment)
        file_path = models.generate_file_path(attachment, "test.pdf")
        self.assert_file_path(file_path, [
            str(self.partner.pk),
            "agreements",
            str(self.agreement.pk),
            "interventions",
            str(self.intervention.pk),
            "amendments",
            str(amendment.pk),
            "test.pdf"
        ], "partners")
        # check against old file path function
        file_path_old = partner_models.get_intervention_amendment_file_path(
            amendment,
            "test.pdf"
        )
        self.assertEqual(file_path, file_path_old)

    def test_intervention_attachment(self):
        intervention_attachment = InterventionAttachmentFactory(
            intervention=self.intervention
        )
        attachment = AttachmentFactory(content_object=intervention_attachment)
        file_path = models.generate_file_path(attachment, "test.pdf")
        self.assert_file_path(file_path, [
            "agreements",
            str(self.agreement.pk),
            "interventions",
            str(self.intervention.pk),
            "attachments",
            str(intervention_attachment.pk),
            "test.pdf"
        ], "partners")
        # check against old file path function
        file_path_old = partner_models.get_intervention_attachments_file_path(
            intervention_attachment,
            "test.pdf"
        )
        self.assertEqual(file_path, file_path_old)

    def test_intervention(self):
        attachment = AttachmentFactory(
            content_object=self.intervention
        )
        file_path = models.generate_file_path(attachment, "test.pdf")
        self.assert_file_path(file_path, [
            "agreements",
            str(self.agreement.pk),
            "interventions",
            str(self.intervention.pk),
            "prc",
            "test.pdf"
        ], "partners")
        # check against old file path function
        file_path_old = partner_models.get_prc_intervention_file_path(
            self.intervention,
            "test.pdf"
        )
        self.assertEqual(file_path, file_path_old)

    def test_agreement_amendment(self):
        amendment = AgreementAmendmentFactory(agreement=self.agreement)
        attachment = AttachmentFactory(content_object=amendment)
        file_path = models.generate_file_path(attachment, "test.pdf")
        self.assert_file_path(file_path, [
            str(self.partner.pk),
            "agreements",
            self.agreement.base_number.strip("/"),
            "amendments",
            str(amendment.number),
            "test.pdf"
        ], "agreementamendment")
        # check against old file path function
        # except new paths do not have '//'
        file_path_old = partner_models.get_agreement_amd_file_path(
            amendment,
            "test.pdf"
        )
        self.assertEqual(file_path, file_path_old.replace("//", "/"))

    def test_default(self):
        file_type = AttachmentFileTypeFactory()
        attachment = AttachmentFactory(content_object=file_type)
        file_path = models.generate_file_path(attachment, "test.pdf")
        self.assert_file_path(file_path, [
            connection.schema_name,
            "files",
            "attachments",
            "filetype",
            attachment.code,
            str(file_type.pk),
            "test.pdf"
        ])

    def test_exception(self):
        attachment = AttachmentFactory(content_object=self.partner)
        with self.assertRaisesRegexp(ValueError, "Unhandled model"):
            models.generate_file_path(attachment, "test.pdf")


class TestFileType(BaseTenantTestCase):
    def test_str(self):
        instance = AttachmentFileTypeFactory(label='xyz')
        self.assertIn(u'xyz', six.text_type(instance))

        instance = AttachmentFileTypeFactory(label='R\xe4dda Barnen')
        self.assertIn('R\xe4dda Barnen', six.text_type(instance))


class TestAttachments(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.simple_object = AttachmentFileTypeFactory()

    def test_str(self):
        instance = AttachmentFactory(
            file=SimpleUploadedFile('simple_file.txt', b'these are the file contents!'),
            content_object=self.simple_object
        )
        self.assertIn('simple_file', six.text_type(instance))

        instance = AttachmentFactory(
            file=SimpleUploadedFile('simple_file.txt', u'R\xe4dda Barnen'.encode('utf-8')),
            content_object=self.simple_object
        )
        self.assertIn('simple_file', six.text_type(instance))

    def test_filename(self):
        instance = AttachmentFactory(
            file="test.pdf",
            content_object=self.simple_object
        )
        self.assertEqual(instance.filename, "test.pdf")

    def test_filename_hyperlink(self):
        instance = AttachmentFactory(
            hyperlink="http://example.com/test_file.txt",
            content_object=self.simple_object
        )
        self.assertEqual(instance.filename, "test_file.txt")

    def test_valid_file(self):
        valid_file_attachment = AttachmentFactory(
            # Note: file content is intended to be a byte-string here.
            file=SimpleUploadedFile('simple_file.txt', b'these are the file contents!'),
            content_object=self.simple_object
        )
        valid_file_attachment.clean()
        self.assertIsNotNone(valid_file_attachment.file)
        self.assertEqual(valid_file_attachment.url, valid_file_attachment.file.url)

    def test_valid_hyperlink(self):
        valid_hyperlink_attachment = AttachmentFactory(
            hyperlink='http://example.com/test_file.txt', content_object=self.simple_object
        )
        valid_hyperlink_attachment.clean()
        self.assertIsNotNone(valid_hyperlink_attachment.hyperlink)
        self.assertEqual(valid_hyperlink_attachment.url, valid_hyperlink_attachment.hyperlink)

    def test_invalid(self):
        invalid_attachment = AttachmentFactory(content_object=self.simple_object)
        with self.assertRaises(ValidationError):
            invalid_attachment.clean()
