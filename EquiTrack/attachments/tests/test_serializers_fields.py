from __future__ import absolute_import, division, print_function, unicode_literals

import base64

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import serializers
from rest_framework.metadata import SimpleMetadata

from attachments import serializers_fields as fields
from attachments.metadata import ModelChoiceFieldMixin
from attachments.models import Attachment, FileType
from attachments.tests.factories import AttachmentFactory, FileTypeFactory
from EquiTrack.tests.mixins import FastTenantTestCase


class TestBase64FileField(FastTenantTestCase):
    def setUp(self):
        self.test_file_content = 'these are the file contents!'

    def test_valid(self):
        valid_base64_file = 'data:text/plain;base64,{}'.format(base64.b64encode(self.test_file_content))
        self.assertIsNotNone(fields.Base64FileField().to_internal_value(valid_base64_file))

    def test_invalid(self):
        with self.assertRaises(serializers.ValidationError):
            fields.Base64FileField().to_internal_value(42)

    def test_corrupted(self):
        corrupted_base64_file = 'data;base64,{}'.format(base64.b64encode(self.test_file_content))
        with self.assertRaises(serializers.ValidationError):
            fields.Base64FileField().to_internal_value(corrupted_base64_file)


class TestSerializer(serializers.Serializer):
    file_type = fields.FileTypeModelChoiceField(queryset=FileType.objects.filter(code='code1'))


class TestMetadata(ModelChoiceFieldMixin, SimpleMetadata):
    pass


class TestModelChoiceFileField(FastTenantTestCase):
    def setUp(self):
        self.code1_obj = FileTypeFactory(code='code1')
        self.code2_obj = FileTypeFactory(code='code2')

    def test_valid_serializer(self):
        valid_serializer = TestSerializer(data={'file_type': self.code1_obj.pk})
        self.assertTrue(valid_serializer.is_valid())

    def test_invalid_serializer(self):
        invalid_serializer = TestSerializer(data={'file_type': self.code2_obj.pk})
        self.assertFalse(invalid_serializer.is_valid())
        self.assertIn('file_type', invalid_serializer.errors)
        self.assertIn(
            'Invalid option "{pk_value}" - option does not available.'.format(pk_value=self.code2_obj.pk),
            invalid_serializer.errors['file_type']
        )

    def test_metadata(self):
        file_type_choices = map(
            lambda x: x['value'],
            TestMetadata().get_serializer_info(TestSerializer())['file_type']['choices']
        )
        self.assertIn(self.code1_obj.pk, file_type_choices)
        self.assertNotIn(self.code2_obj.pk, file_type_choices)


class TestAttachmentSingleFileField(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.code = "code1"
        cls.file_type = FileTypeFactory(code=cls.code)
        cls.file_data = SimpleUploadedFile(
            'hello_world.txt',
            u'hello world!'.encode('utf-8')
        )

    def test_no_attribute(self):
        field = fields.AttachmentSingleFileField(source="wrong")
        self.assertIsNone(field.get_attribute(self.file_type))

    def test_no_attachment(self):
        self.file_type.attachment = Attachment.objects.filter(code=self.code)
        field = fields.AttachmentSingleFileField(source="attachment")
        self.assertIsNone(field.get_attribute(self.file_type))

    def test_attachment(self):
        self.file_type.attachment = Attachment.objects.filter(code=self.code)
        field = fields.AttachmentSingleFileField(source="attachment")
        attachment = AttachmentFactory(
            file_type=self.file_type,
            content_object=self.file_type,
            code=self.code,
            file=self.file_data,
        )
        self.assertEqual(field.get_attribute(self.file_type), attachment.file)

    def test_last_attachment(self):
        self.file_type.attachment = Attachment.objects.filter(code=self.code)
        field = fields.AttachmentSingleFileField(source="attachment")
        AttachmentFactory(
            file_type=self.file_type,
            content_object=self.file_type,
            code=self.code,
        )
        attachment = AttachmentFactory(
            file_type=self.file_type,
            content_object=self.file_type,
            code=self.code,
            file=self.file_data,
        )
        self.assertEqual(field.get_attribute(self.file_type), attachment.file)
