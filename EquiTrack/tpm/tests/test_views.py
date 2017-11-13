from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import timedelta, datetime

from django.core.management import call_command

from rest_framework import status

from EquiTrack.tests.mixins import APITenantTestCase
from tpm.models import TPMActionPoint
from tpm.tests.base import TPMTestCaseMixin
from tpm.tests.factories import TPMPartnerFactory, TPMVisitFactory, UserFactory


class TestExportMixin(object):
    def _test_export(self, user, url_postfix, status_code=status.HTTP_200_OK):
        if not url_postfix.endswith('/'):
            url_postfix += '/'

        response = self.forced_auth_req(
            'get',
            '/api/tpm/{}'.format(url_postfix),
            user=user
        )

        self.assertEqual(response.status_code, status_code)
        if status_code == status.HTTP_200_OK:
            self.assertIn(response._headers['content-disposition'][0], 'Content-Disposition')


class TestTPMVisitViewSet(TestExportMixin, TPMTestCaseMixin, APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_tpm_permissions', verbosity=0)

        cls.pme_user = UserFactory(pme=True)
        cls.unicef_user = UserFactory(unicef_user=True)
        cls.tpm_user = UserFactory(tpm=True)

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

    def test_unicef_list_view(self):
        tpm_visits = [TPMVisitFactory(), TPMVisitFactory()]

        self._test_list_view(self.pme_user, tpm_visits)
        self._test_list_view(self.unicef_user, tpm_visits)

    def test_tpm_list_view(self):
        TPMVisitFactory()

        # drafts shouldn't be available for tpm
        self._test_list_view(self.tpm_user, [])

        visit = TPMVisitFactory(status='assigned',
                                tpm_partner=self.tpm_user.tpm_tpmpartnerstaffmember.tpm_partner,
                                tpm_partner_focal_points=[self.tpm_user.tpm_tpmpartnerstaffmember])

        self._test_list_view(self.tpm_user, [visit])

    def test_create_empty(self):
        create_response = self.forced_auth_req(
            'post',
            '/api/tpm/visits/',
            user=self.pme_user,
            data={}
        )

        self.assertEquals(create_response.status_code, status.HTTP_201_CREATED)

    def test_action_points(self):
        visit = TPMVisitFactory(status='tpm_reported', unicef_focal_points__count=1)
        unicef_focal_point = visit.unicef_focal_points.first()
        self.assertEquals(TPMActionPoint.objects.filter(tpm_visit=visit).count(), 0)

        response = self.forced_auth_req(
            'patch',
            '/api/tpm/visits/{}/'.format(visit.id),
            user=unicef_focal_point,
            data={
                'action_points': [
                    {
                        "person_responsible": visit.tpm_partner.staff_members.first().user.id,
                        "due_date": (datetime.now().date() + timedelta(days=5)).strftime('%Y-%m-%d'),
                        "description": "Description",
                    }
                ]
            }
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertNotEquals(TPMActionPoint.objects.filter(tpm_visit=visit).count(), 0)

    def test_visits_csv(self):
        self._test_export(self.pme_user, 'visits/export')

    def test_activities_csv(self):
        self._test_export(self.pme_user, 'visits/activities/export')

    def test_locations_csv(self):
        self._test_export(self.pme_user, 'visits/locations/export')

    def test_visit_letter(self):
        visit = TPMVisitFactory(status='tpm_accepted')
        self._test_export(self.pme_user, 'visits/{}/visit-letter'.format(visit.id))


class TestTPMStaffMembersViewSet(TestExportMixin, TPMTestCaseMixin, APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tpm_partner = TPMPartnerFactory()

        cls.pme_user = UserFactory(pme=True)
        cls.unicef_user = UserFactory(unicef_user=True)
        cls.tpm_user = UserFactory(tpm=True, tpm_partner=cls.tpm_partner)

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
            user=self.tpm_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'get',
            '/api/tpm/partners/{0}/staff-members/'.format(self.tpm_partner.id),
            user=self.unicef_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

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
            user=self.tpm_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'get',
            '/api/tpm/partners/{0}/staff-members/{1}/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            user=self.unicef_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_create_view(self):
        user_data = {
            "user": {
                "email": "test_email_1@gmail.com",
                "first_name": "John",
                "last_name": "Doe"
            }
        }

        response = self.forced_auth_req(
            'post',
            '/api/tpm/partners/{0}/staff-members/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            data=user_data,
            user=self.pme_user
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        response = self.forced_auth_req(
            'post',
            '/api/tpm/partners/{0}/staff-members/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            data=user_data,
            user=self.tpm_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.forced_auth_req(
            'post',
            '/api/tpm/partners/{0}/staff-members/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            data=user_data,
            user=self.unicef_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_view(self):
        user_data = {
            "user": {
                "first_name": "John",
                "last_name": "Doe"
            }
        }

        response = self.forced_auth_req(
            'patch',
            '/api/tpm/partners/{0}/staff-members/{1}/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            data=user_data,
            user=self.pme_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'patch',
            '/api/tpm/partners/{0}/staff-members/{1}/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            data=user_data,
            user=self.tpm_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.forced_auth_req(
            'patch',
            '/api/tpm/partners/{0}/staff-members/{1}/'.format(
                self.tpm_partner.id,
                self.tpm_partner.staff_members.first().id
            ),
            data=user_data,
            user=self.unicef_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_members_csv(self):
        self._test_export(self.pme_user, 'partners/{}/staff-members/export'.format(self.tpm_partner.id))


class TestTPMPartnerViewSet(TestExportMixin, TPMTestCaseMixin, APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tpm_partner = TPMPartnerFactory()
        cls.second_tpm_partner = TPMPartnerFactory()

        cls.pme_user = UserFactory(pme=True)
        cls.unicef_user = UserFactory(unicef_user=True)
        cls.tpm_user = UserFactory(tpm=True, tpm_partner=cls.tpm_partner)

    def _test_list_view(self, user, expected_firms):
        response = self.forced_auth_req(
            'get',
            '/api/tpm/partners/',
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            sorted(map(lambda x: x['id'], response.data['results'])),
            sorted(map(lambda x: x.id, expected_firms))
        )

    def _test_list_options(self, user, can_create=True, writable_fields=None):
        response = self.forced_auth_req(
            'options',
            '/api/tpm/partners/',
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)

        if can_create:
            self.assertIn('POST', response.data['actions'])
            self.assertListEqual(
                sorted(writable_fields or []),
                sorted(response.data['actions']['POST'].keys())
            )
        else:
            self.assertNotIn('POST', response.data['actions'])

    def _test_detail_options(self, user, can_update=True, writable_fields=None):
        response = self.forced_auth_req(
            'options',
            '/api/tpm/partners/{}/'.format(self.tpm_partner.id),
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)

        if can_update:
            self.assertIn('PUT', response.data['actions'])
            self.assertListEqual(
                sorted(writable_fields or []),
                sorted(response.data['actions']['PUT'].keys())
            )
        else:
            self.assertNotIn('PUT', response.data['actions'])

    def test_pme_list_view(self):
        self._test_list_view(self.pme_user, [self.tpm_partner, self.second_tpm_partner])

    def test_unicef_list_view(self):
        self._test_list_view(self.unicef_user, [self.tpm_partner, self.second_tpm_partner])

    def test_tpm_partner_list_view(self):
        self._test_list_view(self.tpm_user, [self.tpm_partner])

    def test_pme_list_options(self):
        self._test_list_options(
            self.pme_user,
            writable_fields=['attachments', 'email', 'hidden', 'phone_number']
        )

    def test_tpm_partner_list_options(self):
        self._test_list_options(self.tpm_user, can_create=False)

    def test_pme_detail_options(self):
        self._test_detail_options(
            self.pme_user,
            writable_fields=['attachments', 'email', 'hidden', 'phone_number']
        )

    def test_tpm_partner_detail_options(self):
        self._test_detail_options(self.tpm_user, can_update=False)

    def test_partners_csv(self):
        self._test_export(self.pme_user, 'partners/export')
