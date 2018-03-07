from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

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
        self.assertIsNone(self.attachment.uploaded_by)
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
        self.assertEqual(attachment_update.uploaded_by, self.unicef_staff)

    def test_patch(self):
        self.assertFalse(self.attachment.file)
        self.assertIsNone(self.attachment.uploaded_by)
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
        self.assertEqual(attachment_update.uploaded_by, self.unicef_staff)

    def test_put_target(self):
        """Ensure update only affects specified attachment"""
        attachment = AttachmentFactory(
            file_type=self.file_type,
            code=self.code,
            content_object=self.file_type
        )
        self.assertFalse(self.attachment.file)
        self.assertFalse(attachment.file)
        self.assertIsNone(self.attachment.uploaded_by)
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
        self.assertEqual(attachment_update.uploaded_by, self.unicef_staff)
        other_attachment_update = Attachment.objects.get(pk=attachment.pk)
        self.assertFalse(other_attachment_update.file)


class TestAttachmentListView(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.code = "test_code"
        cls.file_type = FileTypeFactory(code=cls.code)
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.url = reverse("attachments:list")

    def test_get_empty(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_no_file(self):
        attachment = AttachmentFactory(
            file_type=self.file_type,
            code=self.code,
            content_object=self.file_type
        )
        self.assertFalse(attachment.file)
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_file(self):
        attachment = AttachmentFactory(
            file_type=self.file_type,
            code=self.code,
            file="sample.pdf",
            content_object=self.file_type
        )
        self.assertTrue(attachment.file)
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data)

    def test_get_hyperlink(self):
        attachment = AttachmentFactory(
            file_type=self.file_type,
            code=self.code,
            hyperlink="https://example.com/sample.pdf",
            content_object=self.file_type
        )
        self.assertTrue(attachment.hyperlink)
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data)

    def test_filter_not_found(self):
        AttachmentFactory(
            file_type=self.file_type,
            code=self.code,
            file="sample.pdf",
            content_object=self.file_type
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"file_type": 404}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data)

    def test_filter_invalid(self):
        AttachmentFactory(
            file_type=self.file_type,
            code=self.code,
            file="sample.pdf",
            content_object=self.file_type
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"wrong": self.file_type.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data)

    def test_filter_file_type(self):
        AttachmentFactory(
            file_type=self.file_type,
            code=self.code,
            file="sample.pdf",
            content_object=self.file_type
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"file_type": self.file_type.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data)

    def test_filter_before(self):
        attachment = AttachmentFactory(
            file_type=self.file_type,
            code=self.code,
            file="sample.pdf",
            content_object=self.file_type
        )
        before = attachment.modified + datetime.timedelta(days=1)
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"before": before.strftime("%Y-%m-%d")}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data)

    def test_filter_after(self):
        attachment = AttachmentFactory(
            file_type=self.file_type,
            code=self.code,
            file="sample.pdf",
            content_object=self.file_type
        )
        after = attachment.modified - datetime.timedelta(days=1)
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"after": after.strftime("%Y-%m-%d")}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data)

    def test_filter_uploaded_by(self):
        AttachmentFactory(
            file_type=self.file_type,
            code=self.code,
            file="sample.pdf",
            content_object=self.file_type,
            uploaded_by=self.unicef_staff,
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"uploaded_by": self.unicef_staff.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data)
