from unittest import skip

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.partners.models import InterventionAmendment
from etools.applications.partners.tests.factories import InterventionAmendmentFactory
from etools.applications.partners.tests.test_epd_management.base import BaseTestCase


class TestAmendmentsManagement(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.example_attachment = AttachmentFactory(
            file=SimpleUploadedFile('hello_world.txt', b'hello world!'),
        )

    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['amendments'], True)
        self.assertEqual(response.data['permissions']['edit']['amendments'], False)

    def test_partnership_manager_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['amendments'], True)
        self.assertEqual(response.data['permissions']['edit']['amendments'], True)

    def test_partnership_manager_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['amendments'], True)
        self.assertEqual(response.data['permissions']['edit']['amendments'], False)

    def test_partner_permissions_unicef_court(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['amendments'], True)
        self.assertEqual(response.data['permissions']['edit']['amendments'], False)

    def test_partner_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['amendments'], True)
        self.assertEqual(response.data['permissions']['edit']['amendments'], True)

    # test functionality
    def test_add(self):
        self.assertEqual(self.draft_intervention.amendments.count(), 0)
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'types': [InterventionAmendment.OTHER],
                'other_description': 'test',
                'signed_amendment_attachment': self.example_attachment.pk,
                'signed_date': '1970-01-01',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.draft_intervention.amendments.count(), 1)

    def test_update(self):
        amendment = InterventionAmendmentFactory(intervention=self.draft_intervention)
        response = self.forced_auth_req(
            'patch',
            reverse('partners_api:intervention-amendments-del', args=[amendment.pk]),
            user=self.partnership_manager,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, response.data)

    def test_destroy(self):
        amendment = InterventionAmendmentFactory(intervention=self.draft_intervention)
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:intervention-amendments-del', args=[amendment.pk]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertEqual(self.draft_intervention.amendments.count(), 0)

    def test_partner_add(self):
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
            data={
                'types': [InterventionAmendment.OTHER],
                'other_description': 'test',
                'signed_amendment_attachment': self.example_attachment.pk,
                'signed_date': '1970-01-01',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partner_destroy(self):
        amendment = InterventionAmendmentFactory(intervention=self.draft_intervention)
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:intervention-amendments-del', args=[amendment.pk]),
            user=self.partner_focal_point,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @skip('real permissions for amendments view are not synced with permissions matrix')
    def test_add_for_ended_intervention(self):
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[self.ended_intervention.pk]),
            user=self.partnership_manager,
            data={
                'types': [InterventionAmendment.OTHER],
                'other_description': 'test',
                'signed_amendment_attachment': self.example_attachment.pk,
                'signed_date': '1970-01-01',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @skip('real permissions for amendments view are not synced with permissions matrix')
    def test_destroy_for_ended_intervention(self):
        amendment = InterventionAmendmentFactory(intervention=self.ended_intervention)
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:intervention-amendments-del', args=[amendment.pk]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
