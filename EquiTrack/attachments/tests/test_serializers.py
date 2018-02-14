from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.translation import ugettext as _

from attachments.models import Attachment
from attachments.serializers import (
    AttachmentFileUploadSerializer,
    Base64AttachmentSerializer,
)
from attachments.tests.factories import AttachmentFactory, FileTypeFactory
from EquiTrack.tests.mixins import FastTenantTestCase


class TestAttachmentsModels(FastTenantTestCase):
    def setUp(self):
        self.file_type = FileTypeFactory()
        self.file_name = 'simple_file.txt'
        file_content = 'these are the file contents!'
        self.base64_file = 'data:text/plain;base64,{}'.format(base64.b64encode(file_content))

    def test_invalid(self):
        invalid_serializer = Base64AttachmentSerializer(data={
            'file_type': self.file_type.pk,
        })
        self.assertFalse(invalid_serializer.is_valid())
        self.assertIn('non_field_errors', invalid_serializer.errors)
        self.assertIn(_('Please provide file or hyperlink.'), invalid_serializer.errors['non_field_errors'])

    def test_valid(self):
        valid_serializer = Base64AttachmentSerializer(data={
            'file': self.base64_file,
            'file_name': self.file_name,
            'file_type': self.file_type.pk,
        })
        self.assertTrue(valid_serializer.is_valid())
        attachment_instance = valid_serializer.save(content_object=self.file_type)
        self.assertTrue(
            os.path.splitext(os.path.split(attachment_instance.file.url)[-1])[0].startswith(
                os.path.splitext(self.file_name)[0]
            )
        )


class TestAttachmentFileUploadSerializer(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.code = "test_code"
        cls.file_type = FileTypeFactory(code=cls.code)

    def setUp(self):
        self.attachment = AttachmentFactory(
            file_type=self.file_type,
            code=self.code,
            content_object=self.file_type
        )
        self.file_data = SimpleUploadedFile(
            'hello_world.txt',
            u'hello world!'.encode('utf-8')
        )

    def test_upload(self):
        self.assertFalse(self.attachment.file)
        serializer = AttachmentFileUploadSerializer(
            instance=self.attachment,
            data={"file": self.file_data}
        )
        self.assertTrue(serializer.is_valid())
        instance = serializer.save()
        self.assertTrue(instance.file)
        attachment_update = Attachment.objects.get(pk=self.attachment.pk)
        self.assertTrue(attachment_update.file)
