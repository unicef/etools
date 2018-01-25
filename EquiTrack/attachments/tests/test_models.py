from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from attachments.tests.factories import AttachmentFactory, FileTypeFactory
from EquiTrack.tests.mixins import TenantTestCase


class TestAttachmentsModels(TenantTestCase):
    def setUp(self):
        self.simple_object = FileTypeFactory()

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
