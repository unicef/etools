from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.partners.models import FileType
from etools.applications.partners.tests.factories import FileTypeFactory
from etools.applications.partners.tests.test_epd_management.base import BaseTestCase


class TestFinalPartnershipReviewManagement(BaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        FileTypeFactory(name=FileType.FINAL_PARTNERSHIP_REVIEW)
        cls.example_attachment = AttachmentFactory(
            file=SimpleUploadedFile('hello_world.txt', b'hello world!'),
        )
        call_command('tenant_loaddata', 'attachments_file_types', verbosity=0)

    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['final_partnership_review'], True)
        self.assertEqual(response.data['permissions']['edit']['final_partnership_review'], False)
        self.assertEqual(response.data['permissions']['view']['date_partnership_review_performed'], True)
        self.assertEqual(response.data['permissions']['edit']['date_partnership_review_performed'], False)

    def test_partnership_manager_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['final_partnership_review'], True)
        self.assertEqual(response.data['permissions']['edit']['final_partnership_review'], False)
        self.assertEqual(response.data['permissions']['view']['date_partnership_review_performed'], True)
        self.assertEqual(response.data['permissions']['edit']['date_partnership_review_performed'], False)

    def test_partnership_manager_permissions_ended(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['final_partnership_review'], True)
        self.assertEqual(response.data['permissions']['edit']['final_partnership_review'], True)
        self.assertEqual(response.data['permissions']['view']['date_partnership_review_performed'], True)
        self.assertEqual(response.data['permissions']['edit']['date_partnership_review_performed'], True)

    def test_partner_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['final_partnership_review'], False)
        self.assertEqual(response.data['permissions']['edit']['final_partnership_review'], False)
        self.assertEqual(response.data['permissions']['view']['date_partnership_review_performed'], False)
        self.assertEqual(response.data['permissions']['edit']['date_partnership_review_performed'], False)

    # test functionality
    def test_update(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
            user=self.partnership_manager,
            data={
                'final_partnership_review': self.example_attachment.id,
                'date_partnership_review_performed': self.ended_intervention.end,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['edit']['final_partnership_review'], True)
        self.assertEqual(response.data['permissions']['edit']['date_partnership_review_performed'], True)
        self.assertIn('hello_world.txt', response.data['final_partnership_review']['attachment'])
        self.assertEqual(
            self.ended_intervention.final_partnership_review.get().pk,
            self.example_attachment.pk
        )

    def test_update_final_partnership_review_permissions_restricted(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'final_partnership_review': self.example_attachment.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0], 'Cannot change fields while in draft: final_partnership_review')

    def test_update_date_partnership_review_performed_permissions_restricted(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'date_partnership_review_performed': self.ended_intervention.end,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0], 'Cannot change fields while in draft: date_partnership_review_performed')
