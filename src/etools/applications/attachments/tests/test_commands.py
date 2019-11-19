from django.core.management import call_command

from unicef_attachments.models import Attachment
from unicef_attachments.utils import get_attachment_flat_model

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory


class TestDenormalizeAttachmentCommand(BaseTenantTestCase):
    def test_run(self):
        AttachmentFlat = get_attachment_flat_model()
        user = UserFactory()
        code = "test_code"
        file_type = AttachmentFileTypeFactory()
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


class TestRemovePDPCADocTypeCommand(BaseTenantTestCase):
    def test_run(self):
        file_type_pd = AttachmentFileTypeFactory(name="pd")
        file_type_pca = AttachmentFileTypeFactory(name="pca")
        file_type_signed = AttachmentFileTypeFactory(name="signed_pd/ssfa")
        file_type_attached = AttachmentFileTypeFactory(
            name="attached_agreement",
        )

        attachment_pd = AttachmentFactory(file_type=file_type_pd)
        attachment_pca = AttachmentFactory(file_type=file_type_pca)

        call_command("remove_pd_pca_doc_types")

        for a in Attachment.objects.all():
            if a.pk == attachment_pd.pk:
                self.assertEqual(attachment_pd.file_type, file_type_signed)
            elif a.pk == attachment_pca.pk:
                self.assertEqual(attachment_pca.file_type, file_type_attached)
