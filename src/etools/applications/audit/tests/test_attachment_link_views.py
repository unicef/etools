from django.urls import reverse

from rest_framework import status
from unicef_attachments.models import AttachmentLink

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.audit.tests.factories import (
    AuditFactory,
    EngagementFactory,
    MicroAssessmentFactory,
    SpecialAuditFactory,
    SpotCheckFactory,
    UserFactory,
)
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase


class TestEngagementAttachmentsView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(unicef_user=True)
        cls.engagement = EngagementFactory()
        cls.attachment = AttachmentFactory(content_object=cls.engagement)

    def test_add(self):
        links_qs = AttachmentLink.objects
        self.assertEqual(links_qs.count(), 0)
        create_response = self.forced_auth_req(
            'post',
            reverse('audit:engagement-links', args=[self.engagement.pk]),
            user=self.user,
            data={'attachments': [{'attachment': self.attachment.pk}]}
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('audit:engagement-links', args=[self.engagement.pk]),
            user=self.user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(links_qs.count(), 1)


class TestSpotCheckAttachmentsView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(unicef_user=True)
        cls.spotcheck = SpotCheckFactory()
        cls.attachment = AttachmentFactory(content_object=cls.spotcheck)

    def test_add(self):
        links_qs = AttachmentLink.objects
        self.assertEqual(links_qs.count(), 0)
        create_response = self.forced_auth_req(
            'post',
            reverse('audit:spot-check-links', args=[self.spotcheck.pk]),
            user=self.user,
            data={'attachments': [{'attachment': self.attachment.pk}]}
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('audit:spot-check-links', args=[self.spotcheck.pk]),
            user=self.user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(links_qs.count(), 1)


class TestMicroAssessmentAttachmentsView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(unicef_user=True)
        cls.microassessment = MicroAssessmentFactory()
        cls.attachment = AttachmentFactory(content_object=cls.microassessment)

    def test_add(self):
        links_qs = AttachmentLink.objects
        self.assertEqual(links_qs.count(), 0)
        create_response = self.forced_auth_req(
            'post',
            reverse(
                'audit:micro-assessment-links',
                args=[self.microassessment.pk],
            ),
            user=self.user,
            data={'attachments': [{'attachment': self.attachment.pk}]}
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse(
                'audit:micro-assessment-links',
                args=[self.microassessment.pk],
            ),
            user=self.user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(links_qs.count(), 1)


class TestAuditAttachmentsView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(unicef_user=True)
        cls.audit = AuditFactory()
        cls.attachment = AttachmentFactory(content_object=cls.audit)

    def test_add(self):
        links_qs = AttachmentLink.objects
        self.assertEqual(links_qs.count(), 0)
        create_response = self.forced_auth_req(
            'post',
            reverse('audit:audit-links', args=[self.audit.pk]),
            user=self.user,
            data={'attachments': [{'attachment': self.attachment.pk}]}
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('audit:audit-links', args=[self.audit.pk]),
            user=self.user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(links_qs.count(), 1)


class TestSpecialAuditAttachmentsView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(unicef_user=True)
        cls.specialaudit = SpecialAuditFactory()
        cls.attachment = AttachmentFactory(content_object=cls.specialaudit)

    def test_add(self):
        links_qs = AttachmentLink.objects
        self.assertEqual(links_qs.count(), 0)
        create_response = self.forced_auth_req(
            'post',
            reverse('audit:special-audit-links', args=[self.specialaudit.pk]),
            user=self.user,
            data={'attachments': [{'attachment': self.attachment.pk}]}
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('audit:special-audit-links', args=[self.specialaudit.pk]),
            user=self.user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(links_qs.count(), 1)
