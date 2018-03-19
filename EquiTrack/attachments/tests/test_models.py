from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from attachments.tests.factories import (
    AttachmentFactory,
    AttachmentFileTypeFactory,
)
from EquiTrack.tests.cases import BaseTenantTestCase


class TestFileType(BaseTenantTestCase):
    def test_str(self):
        instance = AttachmentFileTypeFactory(label=b'xyz')
        self.assertIn(b'xyz', str(instance))
        self.assertIn(u'xyz', unicode(instance))

        instance = AttachmentFileTypeFactory(label=u'R\xe4dda Barnen')
        self.assertIn(b'R\xc3\xa4dda Barnen', str(instance))
        self.assertIn(u'R\xe4dda Barnen', unicode(instance))


class TestAttachments(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.simple_object = AttachmentFileTypeFactory()

    def test_str(self):
        instance = AttachmentFactory(
            file=b'these are the file contents!',
            content_object=self.simple_object
        )
        self.assertIn(b'these are the file contents!', str(instance))
        self.assertIn(u'these are the file contents!', unicode(instance))

        instance = AttachmentFactory(
            file=u'R\xe4dda Barnen',
            content_object=self.simple_object
        )
        self.assertIn(b'R\xc3\xa4dda Barnen', str(instance))
        self.assertIn(u'R\xe4dda Barnen', unicode(instance))

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
