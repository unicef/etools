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
        cls.code_1 = "test_code_1"
        cls.file_type_1 = FileTypeFactory(code=cls.code_1)
        cls.code_2 = "test_code_2"
        cls.file_type_2 = FileTypeFactory(code=cls.code_2)
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.user = UserFactory()
        cls.url = reverse("attachments:list")
        cls.attachment_1 = AttachmentFactory(
            file_type=cls.file_type_1,
            code=cls.code_1,
            file="sample1.pdf",
            content_object=cls.file_type_1,
            uploaded_by=cls.unicef_staff
        )
        cls.attachment_2 = AttachmentFactory(
            file_type=cls.file_type_2,
            code=cls.code_2,
            file="sample2.pdf",
            content_object=cls.file_type_2,
            uploaded_by=cls.user
        )

    def test_get_no_file(self):
        attachment = AttachmentFactory(
            file_type=self.file_type_1,
            code=self.code_1,
            content_object=self.file_type_1
        )
        self.assertFalse(attachment.file)
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_file(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_hyperlink(self):
        attachment = AttachmentFactory(
            file_type=self.file_type_1,
            code=self.code_1,
            hyperlink="https://example.com/sample.pdf",
            content_object=self.file_type_1
        )
        self.assertTrue(attachment.hyperlink)
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_filter_not_found(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"file_type": 404}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data)

    def test_filter_invalid(self):
        """If invalid filter param provided, then all attachments
        are provided
        """
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"wrong": self.file_type_1.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_file_type(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"file_type": self.file_type_1.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["filename"],
            self.attachment_1.filename
        )

    def test_filter_file_type_list(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"file_type": [self.file_type_1.pk, self.file_type_2.pk]}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_before(self):
        before = self.attachment_1.modified + datetime.timedelta(days=1)
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"before": before.strftime("%Y-%m-%d")}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_after(self):
        after = self.attachment_1.modified - datetime.timedelta(days=1)
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"after": after.strftime("%Y-%m-%d")}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_uploaded_by(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"uploaded_by": self.unicef_staff.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["filename"],
            self.attachment_1.filename
        )

    def test_filter_uploaded_by_list(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"uploaded_by": [self.unicef_staff.pk, self.user.pk]}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
