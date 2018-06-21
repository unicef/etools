
import base64
import os

from django.utils.translation import ugettext as _

from rest_framework.exceptions import ValidationError

from etools.applications.attachments.serializers import Base64AttachmentSerializer
from etools.applications.attachments.tests.factories import AttachmentFileTypeFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory


class TestAttachmentsSerializer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.file_type = AttachmentFileTypeFactory()
        cls.file_name = 'simple_file.txt'
        file_content = 'these are the file contents!'.encode('utf-8')
        cls.base64_file = 'data:text/plain;base64,{}'.format(base64.b64encode(file_content))

    def test_invalid(self):
        invalid_serializer = Base64AttachmentSerializer(data={
            'file_type': self.file_type.pk,
        }, context={'user': UserFactory()})

        self.assertTrue(invalid_serializer.is_valid())
        # file and hyperlink validation were moved to save in fact
        with self.assertRaises(ValidationError) as ex:
            invalid_serializer.save()

        self.assertIn(_('Please provide file or hyperlink.'), ex.exception.detail)

    def test_valid(self):
        valid_serializer = Base64AttachmentSerializer(data={
            'file': self.base64_file,
            'file_name': self.file_name,
            'file_type': self.file_type.pk,
        }, context={'user': UserFactory()})
        self.assertTrue(valid_serializer.is_valid())
        attachment_instance = valid_serializer.save(content_object=self.file_type)
        self.assertTrue(
            os.path.splitext(os.path.split(attachment_instance.file.url)[-1])[0].startswith(
                os.path.splitext(self.file_name)[0]
            )
        )
