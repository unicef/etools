from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import reverse

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.audit.tests.factories import AuditorUserFactory, AuditPartnerFactory, SpecialAuditFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory


class DownloadAttachmentTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.unicef_user = UserFactory(is_staff=True)
        self.auditor_firm = AuditPartnerFactory()
        self.auditor = AuditorUserFactory(partner_firm=self.auditor_firm, is_staff=False,
                                          profile__countries_available=[connection.tenant])
        self.attachment = AttachmentFactory(
            file=SimpleUploadedFile(
                'simple_file.txt',
                b'these are the file contents!'
            )
        )

    def _test_download(self, attachment, user, expected_status):
        response = self.forced_auth_req(
            'get',
            reverse('attachments:file', args=[attachment.pk]),
            user=user
        )
        self.assertEqual(response.status_code, expected_status)
        return response

    def test_engagement_attachment_unicef(self):
        specialaudit = SpecialAuditFactory()
        self.attachment.content_object = specialaudit
        self.attachment.save()
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_engagement_attachment_authorized_officer(self):
        specialaudit = SpecialAuditFactory()
        specialaudit.staff_members.add(self.auditor.purchase_order_auditorstaffmember)
        self.attachment.content_object = specialaudit
        self.attachment.save()
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_engagement_attachment_unrelated_auditor(self):
        specialaudit = SpecialAuditFactory()
        self.attachment.content_object = specialaudit
        self.attachment.save()
        self._test_download(self.attachment, self.auditor, status.HTTP_403_FORBIDDEN)
