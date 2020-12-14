from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.field_monitoring.tests.base import APIViewSetTestCase
from etools.applications.partners.tests.factories import PartnerStaffFactory
from etools.applications.partners.tests.test_epd_management.base import BaseTestCase
from etools.applications.users.tests.factories import UserFactory


class TestSignedDocumentsManagement(APIViewSetTestCase, BaseTestCase):
    base_view = 'pmp_v3:intervention'

    def setUp(self):
        super().setUp()
        self.review_unicef_data = {
            'review_date_prc': '1970-01-01',
            'submission_date_prc': '1970-01-01',
            'prc_review_attachment': AttachmentFactory(file=SimpleUploadedFile('hello_world.txt', b'hello world!')).pk,
        }
        self.signature_unicef_data = {
            'unicef_signatory': UserFactory().id,
            'signed_pd_attachment': AttachmentFactory(file=SimpleUploadedFile('hello_world.txt', b'hello world!')).pk,
        }
        self.signature_partner_data = {
            'partner_authorized_officer_signatory': PartnerStaffFactory(partner=self.partner).pk,
            'signed_by_partner_date': '1970-01-02',
        }
        self.all_data = {**self.review_unicef_data, **self.review_unicef_data, **self.signature_partner_data}

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

        for field in self.signature_unicef_data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], True, field)

        for field in self.review_unicef_data.keys():
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

        for field in dict(**self.review_unicef_data, **self.signature_unicef_data).keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], False, field)

        for field in self.signature_partner_data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], True, field)

    # test functionality
    def test_base_update(self):
        self._test_update(self.partnership_manager, self.review_intervention, data=self.review_unicef_data)

    def _test_update_fields(self, user, intervention, allowed_fields=None, restricted_fields=None):
        # check in loop because there are only one error will be raised at a moment
        for field, value in (restricted_fields or {}).items():
            # make_detail_request instead of _test_update for more granular asserting
            response = self.make_detail_request(
                user, instance=intervention, method='patch', data={field: value}
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, f'wrong response for {field}')
            self.assertEqual(
                f'Cannot change fields while in {intervention.status}: {field}', response.data[0],
                response.data
            )

        for field, value in (allowed_fields or {}).items():
            self._test_update(user, intervention, data={field: value})

    def test_partnership_manager_update_draft(self):
        self._test_update_fields(
            self.partnership_manager, self.draft_intervention,
            restricted_fields=dict(
                **self.review_unicef_data, **self.signature_unicef_data, **self.signature_partner_data
            ),
            allowed_fields={},
        )

    def test_partnership_manager_update_review(self):
        self._test_update_fields(
            self.partnership_manager, self.review_intervention,
            restricted_fields=dict(**self.signature_unicef_data, **self.signature_partner_data),
            allowed_fields=self.review_unicef_data,
        )

    def test_partnership_manager_update_signature(self):
        self._test_update_fields(
            self.partnership_manager, self.signature_intervention,
            restricted_fields=self.review_unicef_data,
            allowed_fields=self.signature_unicef_data
        )

    def test_partner_update_draft(self):
        self._test_update_fields(self.partner_focal_point, self.draft_intervention, restricted_fields=self.all_data)

    def test_partner_update_review(self):
        self._test_update_fields(self.partner_focal_point, self.review_intervention, restricted_fields=self.all_data)

    def test_partner_update_signature(self):
        self._test_update_fields(
            self.partner_focal_point, self.signature_intervention,
            restricted_fields=dict(**self.review_unicef_data, **self.signature_unicef_data),
            allowed_fields=self.signature_partner_data
        )
