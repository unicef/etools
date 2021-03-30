from etools.applications.attachments import utils
from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.t2f.tests.factories import TravelAttachmentFactory, TravelFactory


class TestGetFileType(BaseTenantTestCase):
    def test_travel_attachment(self):
        travel = TravelFactory()
        travel_attachment = TravelAttachmentFactory(
            travel=travel,
            type="Travel Attachment PDF",
        )
        file_type = AttachmentFileTypeFactory()
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=file_type,
            code="t2f_travel_attachment",
            content_object=travel_attachment,
        )

        self.assertEqual(
            utils.get_file_type(attachment),
            "Travel Attachment PDF",
        )


class TestGetSource(BaseTenantTestCase):
    def test_travel_attachment(self):
        travel = TravelFactory()
        travel_attachment = TravelAttachmentFactory(
            travel=travel,
            type="Travel Attachment PDF",
        )
        file_type = AttachmentFileTypeFactory()
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=file_type,
            code="t2f_travel_attachment",
            content_object=travel_attachment,
        )

        self.assertEqual(
            utils.get_source(attachment),
            "Trips",
        )
