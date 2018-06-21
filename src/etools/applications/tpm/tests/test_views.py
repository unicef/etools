
from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from factory import fuzzy

from rest_framework import status

from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.attachments.tests.factories import AttachmentFileTypeFactory, AttachmentFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import PartnerType
from etools.applications.tpm.models import TPMVisit
from etools.applications.tpm.tests.base import TPMTestCaseMixin
from etools.applications.tpm.tests.factories import TPMPartnerFactory, TPMVisitFactory, _FUZZY_END_DATE
from etools.applications.utils.common.tests.test_utils import TestExportMixin


class TestTPMVisitViewSet(TestExportMixin, TPMTestCaseMixin, BaseTenantTestCase):
    def _test_list_view(self, user, expected_visits):
        response = self.forced_auth_req(
            'get',
            reverse('tpm:visits-list'),
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
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
        TPMVisitFactory(status='unicef_approved', tpm_activities__action_points__count=3)
        self._test_export(self.pme_user, 'tpm:visits-action-points/export')

    def test_visit_action_points_csv(self):
        visit = TPMVisitFactory(status='unicef_approved', tpm_activities__action_points__count=3)
        self._test_export(self.pme_user, 'tpm:action-points-export', args=(visit.id,))

    def test_visit_letter(self):
        visit = TPMVisitFactory(status='tpm_accepted')
        self._test_export(self.pme_user, 'tpm:visits-visit-letter', args=(visit.id,))


class TestTPMActionPointViewSet(TPMTestCaseMixin, BaseTenantTestCase):
    def test_action_point_added(self):
        visit = TPMVisitFactory(status='tpm_reported', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        self.assertEqual(activity.action_points.count(), 0)

        response = self.forced_auth_req(
            'post',
            '/api/tpm/visits/{}/action-points/'.format(visit.id),
            user=self.pme_user,
            data={
                'tpm_activity': activity.id,
                'description': fuzzy.FuzzyText(length=100).fuzz(),
                'due_date': fuzzy.FuzzyDate(timezone.now().date(), _FUZZY_END_DATE).fuzz(),
                'assigned_to': self.unicef_user.id,
                'office': self.pme_user.profile.office.id,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(activity.action_points.count(), 1)
        self.assertIsNotNone(activity.action_points.first().section)

    def _test_action_point_editable(self, action_point, user, editable=True):
        visit = action_point.tpm_activity.tpm_visit

        response = self.forced_auth_req(
            'options',
            '/api/tpm/visits/{}/action-points/{}/'.format(visit.id, action_point.id),
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if editable:
            self.assertIn('PUT', response.data['actions'].keys())
            self.assertCountEqual(
                ['assigned_to', 'high_priority', 'due_date', 'description', 'office', 'tpm_activity'],
                response.data['actions']['PUT'].keys()
            )
        else:
            self.assertNotIn('PUT', response.data['actions'].keys())

    def test_action_point_editable_by_pme(self):
        visit = TPMVisitFactory(status='tpm_reported', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='pre_completed')

        self._test_action_point_editable(action_point, self.pme_user)

    def test_action_point_editable_by_author(self):
        visit = TPMVisitFactory(status='tpm_reported', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='pre_completed')

        self._test_action_point_editable(action_point, action_point.author)

    def test_action_point_readonly_by_unicef_user(self):
        visit = TPMVisitFactory(status='tpm_reported', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='pre_completed')

        self._test_action_point_editable(action_point, self.unicef_user, editable=False)

    def test_action_point_editable_by_pme_approved_visit(self):
        visit = TPMVisitFactory(status='unicef_approved', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='pre_completed')

        self._test_action_point_editable(action_point, self.pme_user)

    def test_action_point_editable_by_author_approved_visit(self):
        visit = TPMVisitFactory(status='unicef_approved', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='pre_completed')

        self._test_action_point_editable(action_point, action_point.author)

    def test_action_point_readonly_by_unicef_user_approved_visit(self):
        visit = TPMVisitFactory(status='unicef_approved', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='pre_completed')

        self._test_action_point_editable(action_point, self.unicef_user, editable=False)

    def test_action_point_readonly_on_complete_by_pme(self):
        visit = TPMVisitFactory(status='unicef_approved', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='completed')

        self._test_action_point_editable(action_point, self.pme_user, editable=False)

    def test_action_point_readonly_on_complete_by_author(self):
        visit = TPMVisitFactory(status='unicef_approved', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='completed')

        self._test_action_point_editable(action_point, action_point.assigned_to, editable=False)

    def _test_complete(self, action_point, user, can_complete=True):
        activity = action_point.tpm_activity
        visit = activity.tpm_visit

        response = self.forced_auth_req(
            'post',
            '/api/tpm/visits/{}/action-points/{}/complete/'.format(visit.id, action_point.id),
            user=user
        )

        if can_complete:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['status'], 'completed')
        else:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_action_point_complete_pme(self):
        visit = TPMVisitFactory(status='tpm_reported', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='pre_completed', comments__count=0)

        self._test_complete(action_point, self.pme_user)

    def test_action_point_complete_assignee(self):
        visit = TPMVisitFactory(status='tpm_reported', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='pre_completed', comments__count=0)

        self._test_complete(action_point, action_point.assigned_to)

    def test_action_point_complete_fail_unicef_user(self):
        visit = TPMVisitFactory(status='tpm_reported', tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        action_point = ActionPointFactory(tpm_activity=activity, status='pre_completed', comments__count=0)

        self._test_complete(action_point, self.unicef_user, can_complete=False)


class TestTPMStaffMembersViewSet(TestExportMixin, TPMTestCaseMixin, BaseTenantTestCase):
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
        cls.second_tpm_partner = TPMPartnerFactory()

    def _test_list_view(self, user, expected_firms):
        response = self.forced_auth_req(
            'get',
            reverse('tpm:partners-list'),
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
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
            self.assertCountEqual(
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
            self.assertCountEqual(
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
            writable_fields=['email', 'hidden', 'phone_number']
        )

    def test_tpm_partner_list_options(self):
        self._test_list_options(self.tpm_user, can_create=False)

    def test_pme_detail_options(self):
        self._test_detail_options(
            self.pme_user,
            writable_fields=['email', 'hidden', 'phone_number']
        )

    def test_tpm_partner_detail_options(self):
        self._test_detail_options(self.tpm_user, can_update=False)

    def test_partners_csv(self):
        self._test_export(self.pme_user, 'tpm:partners-export')


class TestPartnerAttachmentsView(TPMTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        partner = TPMPartnerFactory()
        attachments_num = partner.attachments.count()

        AttachmentFactory(content_object=partner)

        response = self.forced_auth_req(
            'get',
            reverse('tpm:partner-attachments-list', args=[partner.id]),
            user=self.pme_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), attachments_num + 1)

    def test_add(self):
        partner = TPMPartnerFactory()

        response = self.forced_auth_req(
            'post',
            reverse('tpm:partner-attachments-list', args=[partner.id]),
            user=self.pme_user,
            request_format='multipart',
            data={
                'file_type': AttachmentFileTypeFactory(code='tpm_partner').id,
                'file': SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8')),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class TestVisitReportAttachmentsView(TPMTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super(TestVisitReportAttachmentsView, cls).setUpTestData()

        cls.visit = TPMVisitFactory(status='tpm_accepted',
                                    tpm_partner=cls.tpm_user.tpmpartners_tpmpartnerstaffmember.tpm_partner,
                                    tpm_partner_focal_points=[cls.tpm_user.tpmpartners_tpmpartnerstaffmember])

    def test_add(self):
        attachments_num = self.visit.report_attachments.count()

        create_response = self.forced_auth_req(
            'post',
            reverse('tpm:visit-report-attachments-list', args=[self.visit.id]),
            user=self.tpm_user,
            request_format='multipart',
            data={
                'file_type': AttachmentFileTypeFactory(code='tpm_report_attachments').id,
                'file': SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8')),
            }
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        response = self.forced_auth_req(
            'get',
            reverse('tpm:visit-report-attachments-list', args=[self.visit.id]),
            user=self.tpm_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), attachments_num + 1)


class TestActivityAttachmentsView(TPMTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super(TestActivityAttachmentsView, cls).setUpTestData()

        cls.visit = TPMVisitFactory(status='draft',
                                    tpm_partner=cls.tpm_user.tpmpartners_tpmpartnerstaffmember.tpm_partner,
                                    tpm_partner_focal_points=[cls.tpm_user.tpmpartners_tpmpartnerstaffmember],
                                    tpm_activities__count=1)
        cls.activity = cls.visit.tpm_activities.first()

    def test_add(self):
        attachments_num = self.activity.report_attachments.count()
        create_response = self.forced_auth_req(
            'post',
            reverse('tpm:activity-attachments-list', args=[self.visit.id]),
            user=self.pme_user,
            request_format='multipart',
            data={
                'object_id': self.activity.id,
                'file_type': AttachmentFileTypeFactory(code='tpm').id,
                'file': SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8')),
            }
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('tpm:activity-attachments-list', args=[self.visit.id]),
            user=self.pme_user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data['results']), attachments_num + 1)


class TestActivityReportAttachmentsView(TPMTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super(TestActivityReportAttachmentsView, cls).setUpTestData()

        cls.visit = TPMVisitFactory(status='tpm_accepted',
                                    tpm_partner=cls.tpm_user.tpmpartners_tpmpartnerstaffmember.tpm_partner,
                                    tpm_partner_focal_points=[cls.tpm_user.tpmpartners_tpmpartnerstaffmember],
                                    tpm_activities__count=1)
        cls.activity = cls.visit.tpm_activities.first()

    def test_add(self):
        attachments_num = self.activity.report_attachments.count()
        create_response = self.forced_auth_req(
            'post',
            reverse('tpm:activity-report-attachments-list', args=[self.visit.id]),
            user=self.tpm_user,
            request_format='multipart',
            data={
                'object_id': self.activity.id,
                'file_type': AttachmentFileTypeFactory(code='tpm_report').id,
                'file': SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8')),
            }
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('tpm:activity-report-attachments-list', args=[self.visit.id]),
            user=self.tpm_user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data['results']), attachments_num + 1)
