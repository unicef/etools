from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from EquiTrack.tests.mixins import FastTenantTestCase
from .factories import AttachmentFactory, FileTypeFactory


class TestAttachmentsModels(FastTenantTestCase):
    def setUp(self):
        self.simple_object = FileTypeFactory()

    def test_valid_file(self):
        valid_file_attachment = AttachmentFactory(
            file=SimpleUploadedFile('simple_file.txt', 'these are the file contents!'),
            object=self.simple_object
        )
        valid_file_attachment.clean()
        self.assertIsNotNone(valid_file_attachment.file)
        self.assertEqual(valid_file_attachment.url, valid_file_attachment.file.url)

    def test_valid_hyperlink(self):
        valid_hyperlink_attachment = AttachmentFactory(
            hyperlink='http://example.com/test_file.txt', object=self.simple_object
        )
        valid_hyperlink_attachment.clean()
        self.assertIsNotNone(valid_hyperlink_attachment.hyperlink)
        self.assertEqual(valid_hyperlink_attachment.url, valid_hyperlink_attachment.hyperlink)

    def test_invalid(self):
        invalid_attachment = AttachmentFactory(object=self.simple_object)
        with self.assertRaises(ValidationError):
            invalid_attachment.clean()
