from collections import namedtuple

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
        self.draft_unicef_data = {
            'submission_date': '1970-01-01',
        }
        self.review_unicef_data = {}
        self.signature_unicef_data = {
            'signed_by_unicef_date': '1970-01-02',
            'unicef_signatory': UserFactory().id,
            'signed_pd_attachment': AttachmentFactory(file=SimpleUploadedFile('hello_world.txt', b'hello world!')).pk,
        }
        self.signature_partner_data = {
            'partner_authorized_officer_signatory': PartnerStaffFactory(partner=self.partner).pk,
            'signed_by_partner_date': '1970-01-02',
        }
        self.contingency_signed_data = {
            'start': '1970-01-02',
            'end': '1970-02-02'
        }
        self.signed_data = {
            **self.contingency_signed_data,
            'planned_budget': {
                'id': self.signed_intervention.planned_budget.pk,
                'total_hq_cash_local': 1300}
        }
        self.all_data = {
            **self.draft_unicef_data, **self.review_unicef_data, **self.review_unicef_data,
            **self.signature_partner_data,
        }

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

        for field in dict(**self.draft_unicef_data, **self.review_unicef_data).keys():
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

        for field in dict(**self.draft_unicef_data, **self.review_unicef_data, **self.signature_unicef_data).keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], False, field)

        for field in self.signature_partner_data.keys():
            self.assertEqual(response.data['permissions']['view'][field], True, field)
            self.assertEqual(response.data['permissions']['edit'][field], True, field)

    def test_user_roles_permissions_on_signed(self):
        users_roles = [self.unicef_user, self.partnership_manager, self.partner_staff_member,
                       self.partner_authorized_officer, self.partner_focal_point]
        for user_role in users_roles:
            response = self.forced_auth_req(
                'get',
                reverse('pmp_v3:intervention-detail', args=[self.signed_intervention.pk]),
                user=user_role,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

            for field in self.signed_data.keys():
                self.assertEqual(response.data['permissions']['view'][field], True, field)
                self.assertEqual(response.data['permissions']['edit'][field], False, field)

    def test_user_roles_permissions_on_contingency_signed(self):
        self.signed_intervention.contingency_pd = True
        self.signed_intervention.activation_protocol = "test"
        self.signed_intervention.save(update_fields=['contingency_pd', 'activation_protocol'])
        # The partnership_manager user is Unicef Focal Point
        self.assertEqual(
            list(self.signed_intervention.unicef_focal_points.values_list('pk', flat=True)),
            [self.partnership_manager.pk]
        )
        EditPermission = namedtuple('EditPermission', 'user, edit_allowed')
        expected_edit_perms = [
            # only Unicef Focal Point can edit start/end dates and HQ contrib
            EditPermission(self.partnership_manager, True),
            EditPermission(self.unicef_user, False),
            EditPermission(self.partner_staff_member, False),
            EditPermission(self.partner_authorized_officer, False),
            EditPermission(self.partner_focal_point, False)
        ]
        for expected in expected_edit_perms:
            response = self.forced_auth_req(
                'get',
                reverse('pmp_v3:intervention-detail', args=[self.signed_intervention.pk]),
                user=expected.user,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

            for field in self.contingency_signed_data.keys():
                self.assertEqual(response.data['permissions']['view'][field], True, field)
                self.assertEqual(response.data['permissions']['edit'][field], expected.edit_allowed, field)

    # test functionality
    def test_base_update(self):
        self._test_update(self.partnership_manager, self.draft_intervention, data=self.draft_unicef_data)

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
            allowed_fields=self.draft_unicef_data,
        )

    def test_partnership_manager_update_review(self):
        self._test_update_fields(
            self.partnership_manager, self.review_intervention,
            restricted_fields=dict(
                **self.draft_unicef_data, **self.signature_unicef_data, **self.signature_partner_data
            ),
            allowed_fields=self.review_unicef_data,
        )

    def test_partnership_manager_update_signature(self):
        self._test_update_fields(
            self.partnership_manager, self.signature_intervention,
            restricted_fields=dict(
                **self.draft_unicef_data, **self.review_unicef_data
            ),
            allowed_fields=self.signature_unicef_data
        )

    def test_partner_update_draft(self):
        for k in self.draft_unicef_data:
            self.all_data.pop(k)
        self._test_update_fields(self.partner_focal_point, self.draft_intervention, restricted_fields=self.all_data)

    def test_partner_update_review(self):
        self._test_update_fields(self.partner_focal_point, self.review_intervention, restricted_fields=self.all_data)

    def test_partner_update_signature(self):
        self._test_update_fields(
            self.partner_focal_point, self.signature_intervention,
            restricted_fields=dict(
                **self.draft_unicef_data, **self.review_unicef_data, **self.signature_unicef_data
            ),
            allowed_fields=self.signature_partner_data
        )

    def test_user_roles_for_update_signed(self):
        users_roles = [self.unicef_user, self.partnership_manager, self.partner_staff_member,
                       self.partner_authorized_officer, self.partner_focal_point]
        for user_role in users_roles:
            self._test_update_fields(
                user_role, self.signed_intervention,
                restricted_fields=dict(
                    **self.draft_unicef_data, **self.review_unicef_data,
                    **self.signature_unicef_data, **self.signed_data
                )
            )

    def test_user_roles_allowed_update_contingency_signed(self):
        self.signed_intervention.contingency_pd = True
        self.signed_intervention.activation_protocol = "test"
        self.signed_intervention.save(update_fields=['contingency_pd', 'activation_protocol'])

        self.assertEqual(
            list(self.signed_intervention.unicef_focal_points.values_list('pk', flat=True)),
            [self.partnership_manager.pk]
        )

        self._test_update_fields(
            self.partnership_manager, self.signed_intervention,
            restricted_fields=dict(
                **self.draft_unicef_data, **self.review_unicef_data,
                **self.signature_unicef_data,
            ),
            allowed_fields=self.contingency_signed_data
        )

    def test_user_roles_restricted_update_contingency_signed(self):
        self.signed_intervention.contingency_pd = True
        self.signed_intervention.activation_protocol = "test"
        self.signed_intervention.save(update_fields=['contingency_pd', 'activation_protocol'])

        restricted_edit_user_roles = [
            self.unicef_user,
            self.partner_staff_member,
            self.partner_authorized_officer,
            self.partner_focal_point
        ]
        for user_role in restricted_edit_user_roles:
            self._test_update_fields(
                user_role, self.signed_intervention,
                restricted_fields=dict(
                    **self.draft_unicef_data, **self.review_unicef_data,
                    **self.signature_unicef_data, **self.contingency_signed_data
                ),
            )
