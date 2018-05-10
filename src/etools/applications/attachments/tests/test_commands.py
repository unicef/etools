from django.core.management import call_command

from etools.applications.attachments.models import AttachmentFlat
from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory


class TestDenormalizeAttachmentCommand(BaseTenantTestCase):
    def test_run(self):
        user = UserFactory()
        code = "test_code"
        file_type = AttachmentFileTypeFactory(code=code)
        attachment = AttachmentFactory(
            file_type=file_type,
            code=code,
            file="sample1.pdf",
            content_object=file_type,
            uploaded_by=user
        )
        flat_qs = AttachmentFlat.objects.filter(attachment=attachment)
        self.assertTrue(flat_qs.exists())
        AttachmentFlat.objects.get(attachment=attachment).delete()
        self.assertFalse(flat_qs.exists())

        call_command("denormalize_attachments")

        self.assertTrue(flat_qs.exists())
