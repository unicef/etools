from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from rest_framework import status

from attachments.models import Attachment
from attachments.tests.factories import AttachmentFactory, FileTypeFactory
from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase


class TestFileUploadView(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.code = "test_code"
        cls.file_type = FileTypeFactory(code=cls.code)
        cls.unicef_staff = UserFactory(is_staff=True)

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
        self.url = reverse("attachments:upload", args=[self.attachment.pk])

    def test_get(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"file": self.file_data}
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_post(self):
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={"file": self.file_data}
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_permission(self):
        user = UserFactory()
        self.assertFalse(self.attachment.file)
        response = self.forced_auth_req(
            "put",
            self.url,
            user=user,
            data={"file": self.file_data},
            request_format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put(self):
        self.assertFalse(self.attachment.file)
        response = self.forced_auth_req(
            "put",
            self.url,
            user=self.unicef_staff,
            data={"file": self.file_data},
            request_format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attachment_update = Attachment.objects.get(pk=self.attachment.pk)
        self.assertTrue(attachment_update.file)
        self.assertTrue(response.data["file"].endswith(attachment_update.url))

    def test_patch(self):
        self.assertFalse(self.attachment.file)
        response = self.forced_auth_req(
            "patch",
            self.url,
            user=self.unicef_staff,
            data={"file": self.file_data},
            request_format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attachment_update = Attachment.objects.get(pk=self.attachment.pk)
        self.assertTrue(attachment_update.file)
        self.assertTrue(response.data["file"].endswith(attachment_update.url))

    def test_put_target(self):
        """Ensure update only affects specified attachment"""
        attachment = AttachmentFactory(
            file_type=self.file_type,
            code=self.code,
            content_object=self.file_type
        )
        self.assertFalse(self.attachment.file)
        self.assertFalse(attachment.file)
        response = self.forced_auth_req(
            "put",
            self.url,
            user=self.unicef_staff,
            data={"file": self.file_data},
            request_format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attachment_update = Attachment.objects.get(pk=self.attachment.pk)
        self.assertTrue(attachment_update.file)
        self.assertTrue(response.data["file"].endswith(attachment_update.url))
        attachment_update = Attachment.objects.get(pk=attachment.pk)
        self.assertFalse(attachment_update.file)
