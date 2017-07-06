from django.core.management import call_command

from rest_framework import status

from EquiTrack.tests.mixins import APITenantTestCase
from .base import TPMTestCaseMixin
from .factories import TPMVisitFactory


class TestTPMVisitViewSet(TPMTestCaseMixin, APITenantTestCase):
    def setUp(self):
        super(TestTPMVisitViewSet, self).setUp()
        call_command('update_tpm_permissions', verbosity=0)

    def _test_list_view(self, user, expected_visits):
        response = self.forced_auth_req(
            'get',
            '/api/tpm/visits/',
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            sorted(map(lambda x: x['id'], response.data['results'])),
            sorted(map(lambda x: x.id, expected_visits))
        )

    def test_list_view(self):
        additional_tpm_visit = TPMVisitFactory()

        self._test_list_view(self.pme_user, [self.tpm_visit, additional_tpm_visit, ])
        self._test_list_view(self.unicef_user, [self.tpm_visit, additional_tpm_visit, ])
        self._test_list_view(self.unicef_focal_point, [self.tpm_visit, additional_tpm_visit, ])

        self._test_list_view(self.tpm_user, [self.tpm_visit, ])

        self._test_list_view(self.usual_user, [])


class TestAuditorStaffMembersViewSet(TPMTestCaseMixin, APITenantTestCase):
    def test_list_view(self):
        response = self.forced_auth_req(
            'get',
            '/api/tpm/partners/{0}/staff-members/'.format(self.tpm_partner.id),
            user=self.pme_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'get',
            '/api/tpm/partners/{0}/staff-members/'.format(self.tpm_partner.id),
            user=self.usual_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_view(self):
        response = self.forced_auth_req(
            'get',
            '/api/tpm/partners/{0}/staff-members/{1}/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            user=self.pme_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'get',
            '/api/tpm/partners/{0}/staff-members/{1}/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            user=self.usual_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_view(self):
        response = self.forced_auth_req(
            'post',
            '/api/tpm/partners/{0}/staff-members/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            data={
                "user": {
                    "email": "test_email_1@gmail.com",
                    "first_name": "John",
                    "last_name": "Doe"
                }
            },
            user=self.pme_user
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        response = self.forced_auth_req(
            'post',
            '/api/tpm/partners/{0}/staff-members/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            data={
                "user": {
                    "email": "test_email_2@gmail.com",
                    "first_name": "John",
                    "last_name": "Doe"
                }
            },
            user=self.usual_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_view(self):
        response = self.forced_auth_req(
            'patch',
            '/api/tpm/partners/{0}/staff-members/{1}/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            data={
                "user": {
                    "first_name": "John",
                    "last_name": "Doe"
                }
            },
            user=self.pme_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'patch',
            '/api/tpm/partners/{0}/staff-members/{1}/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            data={
                "user": {
                    "first_name": "John",
                    "last_name": "Doe"
                }
            },
            user=self.usual_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
