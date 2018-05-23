
import base64
from datetime import datetime

from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.utils import six, timezone
from django.utils.translation import ugettext_lazy as _
from factory import fuzzy

from rest_framework import status

from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.attachments.tests.factories import AttachmentFileTypeFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import PartnerType
from etools.applications.tpm.models import TPMVisit
from etools.applications.tpm.tests.base import TPMTestCaseMixin
from etools.applications.tpm.tests.factories import TPMPartnerFactory, TPMVisitFactory, UserFactory, _FUZZY_END_DATE


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


class TestTPMVisitViewSet(TestExportMixin, TPMTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super(TestTPMVisitViewSet, cls).setUpTestData()
        call_command('update_tpm_permissions', verbosity=0)
        call_command('update_notifications')

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
        six.assertCountEqual(
            self,
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

    def test_add_attachment(self):
        file_type = AttachmentFileTypeFactory(code="tpm")
        file_name = 'simple_file.txt'
        file_content = 'these are the file contents!'.encode('utf-8')
        base64_file = 'data:text/plain;base64,{}'.format(
            base64.b64encode(file_content)
        )
        visit = TPMVisitFactory(
            tpm_activities__count=1,
            tpm_activities__intervention__agreement__partner__partner_type=PartnerType.GOVERNMENT
        )
        activity = visit.tpm_activities.first()
        self.assertEqual(activity.attachments.count(), 0)

        response = self.forced_auth_req(
            'patch',
            reverse('tpm:visits-detail', args=[visit.pk]),
            user=self.pme_user,
            data={
                "tpm_activities": [{
                    "id": activity.pk,
                    "attachments": [
                        {
                            "file_name": file_name,
                            "file": base64_file,
                            "file_type": file_type.pk,
                        }
                    ]
                }]
            }
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data["tpm_activities"][0]["attachments"]))
        self.assertEqual(activity.attachments.count(), 1)

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
                        'locations': existing_activity.locations.all().values_list('id', flat=True),
                        'offices': existing_activity.offices.all().values_list('id', flat=True),
                        'unicef_focal_points': existing_activity.unicef_focal_points.all().values_list('id', flat=True),
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
                        'locations': existing_activity.locations.all().values_list('id', flat=True),
                        'offices': existing_activity.offices.all().values_list('id', flat=True),
                        'unicef_focal_points': existing_activity.unicef_focal_points.all().values_list('id', flat=True),
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
                        'locations': existing_activity.locations.all().values_list('id', flat=True),
                        'offices': existing_activity.offices.all().values_list('id', flat=True),
                        'unicef_focal_points': existing_activity.unicef_focal_points.all().values_list('id', flat=True),
                    }
                ]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tpm_activities', response.data)
        self.assertIn('intervention', response.data['tpm_activities'][0])
        self.assertEqual(response.data['tpm_activities'][0]['intervention'][0], _('This field is required.'))

    def test_delete_activity(self):
        visit = TPMVisitFactory(tpm_activities__count=2, status='draft')

        response = self.forced_auth_req(
            'patch',
            reverse('tpm:visits-detail', args=(visit.id,)),
            user=self.pme_user,
            data={
                'tpm_activities': [{
                    'id': visit.tpm_activities.first().id,
                    '_delete': True
                }]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(visit.tpm_activities.count(), 1)

    def test_author(self):
        create_response = self.forced_auth_req(
            'post',
            reverse('tpm:visits-list'),
            user=self.pme_user,
            data={}
        )

        self.assertEquals(create_response.status_code, status.HTTP_201_CREATED)

        visit = TPMVisit.objects.get(id=create_response.data['id'])
        self.assertEquals(visit.author, self.pme_user)

    def _test_partner(self, expected_status=status.HTTP_201_CREATED, **kwargs):
        partner = TPMPartnerFactory(**kwargs)

        response = self.forced_auth_req(
            'post',
            reverse('tpm:visits-list'),
            user=self.pme_user,
            data={'tpm_partner': partner.id},
        )
        self.assertEqual(response.status_code, expected_status)

        if expected_status == status.HTTP_400_BAD_REQUEST:
            self.assertIn('tpm_partner', response.data)

    def test_blocked_in_vision_partner(self):
        self._test_partner(blocked=True, expected_status=status.HTTP_400_BAD_REQUEST)

    def test_deleted_in_vision_partner(self):
        self._test_partner(deleted_flag=True, expected_status=status.HTTP_400_BAD_REQUEST)

    def test_good_partner(self):
        self._test_partner()

    def test_visits_csv(self):
        self._test_export(self.pme_user, 'tpm:visits-export')

    def test_activities_csv(self):
        self._test_export(self.pme_user, 'tpm:visits-activities/export')

    def test_locations_csv(self):
        self._test_export(self.pme_user, 'tpm:visits-locations/export')

    def test_action_points_csv(self):
        TPMVisitFactory(status='unicef_approved', tpm_activity__action_points__count=3)
        self._test_export(self.pme_user, 'tpm:visits-action-points/export')

    def test_visit_action_points_csv(self):
        visit = TPMVisitFactory(status='unicef_approved', tpm_activity__action_points__count=3)
        self._test_export(self.pme_user, 'tpm:visits-action-points/export', args=(visit.id,))

    def test_visit_letter(self):
        visit = TPMVisitFactory(status='tpm_accepted')
        self._test_export(self.pme_user, 'tpm:visits-visit-letter', args=(visit.id,))


class TestEngagementActionPointViewSet(TPMTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super(TestEngagementActionPointViewSet, cls).setUpTestData()
        call_command('update_tpm_permissions', verbosity=0)
        call_command('update_notifications')

        cls.pme_user = UserFactory(pme=True)
        cls.unicef_user = UserFactory(unicef_user=True)
        cls.tpm_user = UserFactory(tpm=True)

    def test_action_point_added(self):
        visit = TPMVisitFactory(status='tpm_reported', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        self.assertEqual(activity.action_points.count(), 0)

        response = self.forced_auth_req(
            'post',
            '/api/tpm/visits/{}/activities/{}/action-points/'.format(visit.id, activity.id),
            user=self.pme_user,
            data={
                'description': fuzzy.FuzzyText(length=100).fuzz(),
                'due_date': fuzzy.FuzzyDate(timezone.now().date(), _FUZZY_END_DATE).fuzz(),
                'assigned_to': self.unicef_user.id
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(activity.action_points.count(), 1)

    def test_action_point_editable(self):
        visit = TPMVisitFactory(status='tpm_reported', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='pre_completed')

        response = self.forced_auth_req(
            'options',
            '/api/audit/visits/{}/activities/{}/action-points/{}/'.format(visit.id, activity.id, action_point.id),
            user=self.pme_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('PUT', response.data['actions'].keys())
        self.assertListEqual(
            ['assigned_to', 'high_priority', 'due_date', 'description'],
            list(response.data['actions']['PUT'].keys())
        )

    def test_action_point_readonly_on_complete(self):
        visit = TPMVisitFactory(status='unicef_approved', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='completed')

        response = self.forced_auth_req(
            'options',
            '/api/audit/visits/{}/activities/{}/action-points/{}/'.format(visit.id, activity.id, action_point.id),
            user=self.pme_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('PUT', response.data['actions'].keys())

    def test_action_point_complete(self):
        visit = TPMVisitFactory(status='tpm_reported', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='pre_completed', comments__count=0)

        response = self.forced_auth_req(
            'post',
            '/api/audit/visits/{}/activities/{}/action-points/{}/complete/'.format(visit.id, activity.id,
                                                                                   action_point.id),
            user=self.pme_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')


class TestTPMStaffMembersViewSet(TestExportMixin, TPMTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super(TestTPMStaffMembersViewSet, cls).setUpTestData()

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


class TestTPMPartnerViewSet(TestExportMixin, TPMTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super(TestTPMPartnerViewSet, cls).setUpTestData()

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
        six.assertCountEqual(
            self,
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
            six.assertCountEqual(
                self,
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
            six.assertCountEqual(
                self,
                writable_fields or [],
                response.data['actions']['PUT'].keys()
            )
        else:
            self.assertNotIn('PUT', response.data['actions'])

    def test_activation(self):
        partner = TPMPartnerFactory(countries=[])
        # partner is deactivated yet, so wouldn't appear in list
        self._test_list_view(self.pme_user, [self.tpm_partner, self.second_tpm_partner])

        activate_response = self.forced_auth_req(
            'post',
            reverse('tpm:partners-activate', args=(partner.id,)),
            user=self.pme_user
        )
        self.assertEqual(activate_response.status_code, status.HTTP_200_OK)

        self._test_list_view(self.pme_user, [self.tpm_partner, self.second_tpm_partner, partner])

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
