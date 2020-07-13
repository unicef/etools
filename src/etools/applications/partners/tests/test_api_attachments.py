from django.core.management import call_command
from django.urls import reverse

from rest_framework import status
from unicef_attachments.models import FileType

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory


class TestPMPAttachmentFileTypeView(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        call_command("init-attachment-file-types")
        self.user = UserFactory(is_staff=True)

    def test_get(self):
        file_type_qs = FileType.objects.group_by("pmp")
        response = self.forced_auth_req(
            "get",
            reverse('partners_api:attachment-types'),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), file_type_qs.count())
