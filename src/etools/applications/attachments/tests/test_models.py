from django.core.files.uploadedfile import SimpleUploadedFile

from unicef_attachments.utils import get_attachment_flat_model
from etools.applications.attachments.tests.factories import (
    AttachmentFactory,
    AttachmentFileTypeFactory,
)
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase


class TestAttachmentFlat(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.simple_object = AttachmentFileTypeFactory()

    def test_str(self):
        attachment = AttachmentFactory(
            file=SimpleUploadedFile(
                'simple_file.txt', u'R\xe4dda Barnen'.encode('utf-8')
            ),
            content_object=self.simple_object
        )
        flat_qs = get_attachment_flat_model().objects.filter(
            attachment=attachment
        )
        self.assertTrue(flat_qs.exists())
        flat = flat_qs.first()
        self.assertEqual(str(flat), str(attachment.file))
