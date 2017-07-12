from django.core.management import call_command
from django.utils.translation import ugettext as _

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

    def test_create_empty(self):
        create_response = self.forced_auth_req(
            'post',
            '/api/tpm/visits/',
            user=self.pme_user,
            data={}
        )

        self.assertEquals(create_response.status_code, status.HTTP_201_CREATED)

    def test_assign_empty(self):
        create_response = self.forced_auth_req(
            'post',
            '/api/tpm/visits/',
            user=self.pme_user,
            data={}
        )
        self.assertEquals(create_response.status_code, status.HTTP_201_CREATED)

        assign_response = self.forced_auth_req(
            'post',
            '/api/tpm/visits/{}/assign/'.format(create_response.data['id']),
            user=self.pme_user,
            data={}
        )
        self.assertEquals(assign_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tpm_partner', assign_response.data)
        self.assertEquals(assign_response.data['tpm_partner'], _('This field is required.'))

    def test_assign(self):
        partner = self.tpm_visit.tpm_partner
        tpm_activity = self.tpm_visit.tpm_activities.first()
        tpm_sector = tpm_activity.tpm_sectors.first()
        tpm_low_result = tpm_sector.tpm_low_results.first()
        tpm_location = tpm_low_result.tpm_locations.first()

        create_response = self.forced_auth_req(
            'post',
            '/api/tpm/visits/',
            user=self.pme_user,
            data={
                'tpm_partner': partner.id,
                'tpm_activities': [
                    {
                        'tpm_sectors': [
                            {
                                'tpm_low_results': [
                                    {
                                        'tpm_locations': [
                                            {
                                                'location': tpm_location.location.id
                                            }
                                        ],
                                        'result': tpm_low_result.result.id
                                    }
                                ],
                                'sector': tpm_sector.sector.id,
                            }
                        ],
                        'partnership': tpm_activity.partnership.id,
                        'unicef_focal_points': tpm_activity.unicef_focal_points.values_list('id', flat=True)
                    }
                ]
            }
        )
        self.assertEquals(create_response.status_code, status.HTTP_201_CREATED)

        assign_response = self.forced_auth_req(
            'post',
            '/api/tpm/visits/{}/assign/'.format(create_response.data['id']),
            user=self.pme_user,
            data={}
        )

        self.assertEquals(assign_response.status_code, status.HTTP_200_OK)


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
