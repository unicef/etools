from unittest import skip

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.partners.tests.factories import PartnerStaffFactory
from etools.applications.partners.tests.test_epd_management.base import BaseTestCase
from etools.applications.users.tests.factories import UserFactory


@skip('todo: fix this')
class TestSignedDocumentsManagement(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.draft_unicef_data = {
            'submission_date': '1970-01-01',
        }
        self.review_unicef_data = {
            'review_date_prc': '1970-01-01',
            'submission_date_prc': '1970-01-01',
            'prc_review_attachment': AttachmentFactory(file=SimpleUploadedFile('hello_world.txt', b'hello world!')).pk,
        }
        self.unicef_data = {
            'signed_by_unicef_date': '1970-01-02',
            'unicef_signatory': UserFactory().id,
            'signed_pd_attachment': AttachmentFactory(file=SimpleUploadedFile('hello_world.txt', b'hello world!')).pk,
        }
        self.partner_data = {
            'partner_authorized_officer_signatory': PartnerStaffFactory(partner=self.partner).pk,
            'signed_by_partner_date': '1970-01-02',
        }
        self.all_data = {**self.unicef_data, **self.partner_data}

    # test permissions
    def test_unicef_user_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.signature_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        for field in self.all_data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], False, field)

    def test_partnership_manager_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.signature_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        for field in self.unicef_data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], True, field)

        for field in self.partner_data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], False, field)

    def test_partner_permissions_partner_court(self):
        self.signature_intervention.unicef_court = False
        self.signature_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.signature_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        for field in self.unicef_data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], False, field)

        for field in self.partner_data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], True, field)

    # test functionality
    def test_update(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.signature_intervention.pk]),
            user=self.partnership_manager,
            data=self.unicef_data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_unicef_update_partner_fields(self):
        # check in loop because there are only one error will be raised at a moment
        for field, value in self.partner_data.items():
            response = self.forced_auth_req(
                'patch',
                reverse('pmp_v3:intervention-detail', args=[self.signature_intervention.pk]),
                user=self.partnership_manager,
                data={field: value}
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, f'wrong response for {field}')
            self.assertEqual(f'Cannot change fields while in signed: {field}', response.data[0], response.data)

    def test_partner_update(self):
        for field, value in self.unicef_data.items():
            response = self.forced_auth_req(
                'patch',
                reverse('pmp_v3:intervention-detail', args=[self.signature_intervention.pk]),
                user=self.partner_focal_point,
                data={field: value}
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, f'wrong response for {field}')
            self.assertEqual(f'Cannot change fields while in signed: {field}', response.data[0])

    def test_partner_update_partner_fields(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.signature_intervention.pk]),
            user=self.partner_focal_point,
            data=self.partner_data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
