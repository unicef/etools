from django.core.files.uploadedfile import SimpleUploadedFile

from unicef_attachments.utils import get_attachment_flat_model

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.t2f.tests.factories import TravelAttachmentFactory, TravelFactory


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

    def test_trips_excluded(self):
        travel_attachment = TravelAttachmentFactory(
            travel=TravelFactory(),
            type="Travel Attachment PDF",
        )
        flat_qs = get_attachment_flat_model().objects
        flat_count = flat_qs.count()
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=AttachmentFileTypeFactory(code="t2f_travel_attachment"),
            code="t2f_travel_attachment",
            content_object=travel_attachment,
        )

        self.assertEqual(flat_qs.count(), flat_count)
        self.assertTrue(attachment not in flat_qs.all())
