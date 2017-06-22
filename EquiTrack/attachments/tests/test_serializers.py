import base64
import os

from django.utils.translation import ugettext as _

from EquiTrack.tests.mixins import FastTenantTestCase
from ..serializers import Base64AttachmentSerializer
from .factories import FileTypeFactory


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
