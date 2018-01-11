from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import timedelta, datetime

from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from rest_framework import status

from EquiTrack.tests.mixins import APITenantTestCase
from partners.models import PartnerType
from tpm.models import TPMActionPoint
from tpm.tests.base import TPMTestCaseMixin
from tpm.tests.factories import TPMPartnerFactory, TPMVisitFactory, UserFactory


class TestExportMixin(object):
    def _test_export(self, user, url_name, args=tuple(), kwargs=None, status_code=status.HTTP_200_OK):
        response = self.forced_auth_req(
            'get',
            reverse(url_name, args=args, kwargs=kwargs or {}),
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
            reverse('tpm:visits-list'),
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(
            map(lambda x: x['id'], response.data['results']),
            map(lambda x: x.id, expected_visits)
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
                                tpm_partner=self.tpm_user.tpmpartners_tpmpartnerstaffmember.tpm_partner,
                                tpm_partner_focal_points=[self.tpm_user.tpmpartners_tpmpartnerstaffmember])

        self._test_list_view(self.tpm_user, [visit])

    def test_create_empty(self):
        create_response = self.forced_auth_req(
            'post',
            reverse('tpm:visits-list'),
            user=self.pme_user,
            data={}
        )

        self.assertEquals(create_response.status_code, status.HTTP_201_CREATED)

    def test_action_points(self):
        visit = TPMVisitFactory(status='tpm_reported', unicef_focal_points__count=1)
        unicef_focal_point = visit.unicef_focal_points.first()
        self.assertFalse(TPMActionPoint.objects.filter(tpm_visit=visit).exists())

        response = self.forced_auth_req(
            'patch',
            reverse('tpm:visits-detail', args=(visit.id,)),
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
        self.assertTrue(TPMActionPoint.objects.filter(tpm_visit=visit).exists())

    def test_intervention_bilateral_partner(self):
        visit = TPMVisitFactory(
            tpm_activities__count=1,
            tpm_activities__intervention__agreement__partner__partner_type=PartnerType.BILATERAL_MULTILATERAL
        )

        existing_activity = visit.tpm_activities.first()
        self.assertIsNotNone(existing_activity)
        response = self.forced_auth_req(
            'patch',
            reverse('tpm:visits-detail', args=(visit.id,)),
            user=self.pme_user,
            data={
                'tpm_activities': [
                    {
                        'partner': existing_activity.partner.id,
                        'date': datetime.now().date(),
                        'section': existing_activity.section.id,
                        'locations': existing_activity.locations.all().values_list('id', flat=True)
                    }
                ]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_intervention_government_partner(self):
        visit = TPMVisitFactory(
            tpm_activities__count=1,
            tpm_activities__intervention__agreement__partner__partner_type=PartnerType.GOVERNMENT
        )

        existing_activity = visit.tpm_activities.first()
        self.assertIsNotNone(existing_activity)
        response = self.forced_auth_req(
            'patch',
            reverse('tpm:visits-detail', args=(visit.id,)),
            user=self.pme_user,
            data={
                'tpm_activities': [
                    {
                        'partner': existing_activity.partner.id,
                        'date': datetime.now().date(),
                        'section': existing_activity.section.id,
                        'locations': existing_activity.locations.all().values_list('id', flat=True)
                    }
                ]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_intervention_other_partner(self):
        visit = TPMVisitFactory(
            tpm_activities__count=1,
            tpm_activities__intervention__agreement__partner__partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION
        )

        existing_activity = visit.tpm_activities.first()
        self.assertIsNotNone(existing_activity)
        response = self.forced_auth_req(
            'patch',
            reverse('tpm:visits-detail', args=(visit.id,)),
            user=self.pme_user,
            data={
                'tpm_activities': [
                    {
                        'partner': existing_activity.partner.id,
                        'date': datetime.now().date(),
                        'section': existing_activity.section.id,
                        'locations': existing_activity.locations.all().values_list('id', flat=True)
                    }
                ]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tpm_activities', response.data)
        self.assertIn('intervention', response.data['tpm_activities'][0])
        self.assertEqual(response.data['tpm_activities'][0]['intervention'][0], _('This field is required.'))

    def test_visits_csv(self):
        self._test_export(self.pme_user, 'tpm:visits-export')

    def test_activities_csv(self):
        self._test_export(self.pme_user, 'tpm:visits-activities/export')

    def test_locations_csv(self):
        self._test_export(self.pme_user, 'tpm:visits-locations/export')

    def test_visit_letter(self):
        visit = TPMVisitFactory(status='tpm_accepted')
        self._test_export(self.pme_user, 'tpm:visits-visit-letter', args=(visit.id,))


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
            reverse('tpm:tpmstaffmembers-list', args=(self.tpm_partner.id,)),
            user=self.pme_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'get',
            reverse('tpm:tpmstaffmembers-list', args=(self.tpm_partner.id,)),
            user=self.tpm_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'get',
            reverse('tpm:tpmstaffmembers-list', args=(self.tpm_partner.id,)),
            user=self.unicef_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_detail_view(self):
        response = self.forced_auth_req(
            'get',
            reverse('tpm:tpmstaffmembers-detail',
                    args=(self.tpm_partner.id, self.tpm_partner.staff_members.first().id)),
            user=self.pme_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'get',
            reverse('tpm:tpmstaffmembers-detail',
                    args=(self.tpm_partner.id, self.tpm_partner.staff_members.first().id)),
            user=self.tpm_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'get',
            reverse('tpm:tpmstaffmembers-detail',
                    args=(self.tpm_partner.id, self.tpm_partner.staff_members.first().id)),
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
            reverse('tpm:tpmstaffmembers-list', args=(self.tpm_partner.id,)),
            data=user_data,
            user=self.pme_user
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        response = self.forced_auth_req(
            'post',
            reverse('tpm:tpmstaffmembers-list', args=(self.tpm_partner.id,)),
            data=user_data,
            user=self.tpm_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.forced_auth_req(
            'post',
            reverse('tpm:tpmstaffmembers-list', args=(self.tpm_partner.id,)),
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
            reverse('tpm:tpmstaffmembers-detail',
                    args=(self.tpm_partner.id, self.tpm_partner.staff_members.first().id)),
            data=user_data,
            user=self.pme_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.forced_auth_req(
            'patch',
            reverse('tpm:tpmstaffmembers-detail',
                    args=(self.tpm_partner.id, self.tpm_partner.staff_members.first().id)),
            data=user_data,
            user=self.tpm_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.forced_auth_req(
            'patch',
            reverse('tpm:tpmstaffmembers-detail',
                    args=(self.tpm_partner.id, self.tpm_partner.staff_members.first().id)),
            data=user_data,
            user=self.unicef_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_members_csv(self):
        self._test_export(self.pme_user, 'tpm:tpmstaffmembers-export', args=(self.tpm_partner.id,))


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
            reverse('tpm:partners-list'),
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertItemsEqual(
            map(lambda x: x['id'], response.data['results']),
            map(lambda x: x.id, expected_firms)
        )

    def _test_list_options(self, user, can_create=True, writable_fields=None):
        response = self.forced_auth_req(
            'options',
            reverse('tpm:partners-list'),
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)

        if can_create:
            self.assertIn('POST', response.data['actions'])
            self.assertItemsEqual(
                writable_fields or [],
                response.data['actions']['POST'].keys()
            )
        else:
            self.assertNotIn('POST', response.data['actions'])

    def _test_detail_options(self, user, can_update=True, writable_fields=None):
        response = self.forced_auth_req(
            'options',
            reverse('tpm:partners-detail', args=(self.tpm_partner.id,)),
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)

        if can_update:
            self.assertIn('PUT', response.data['actions'])
            self.assertItemsEqual(
                writable_fields or [],
                response.data['actions']['PUT'].keys()
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
        self._test_export(self.pme_user, 'tpm:partners-export')
