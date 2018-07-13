from datetime import date

from django.core.management import call_command
from django.core.urlresolvers import reverse
from factory import fuzzy

from rest_framework import status

from etools.applications.action_points.tests.base import ActionPointsTestCaseMixin
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.audit.tests.factories import MicroAssessmentFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.reports.tests.factories import SectionFactory
from etools.applications.t2f.tests.factories import TravelFactory
from etools.applications.tpm.tests.factories import UserFactory, TPMVisitFactory
from etools.applications.utils.common.tests.test_utils import TestExportMixin


class TestActionPointViewSet(TestExportMixin, ActionPointsTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_action_points_permissions', verbosity=0)

        cls.pme_user = UserFactory(pme=True)
        cls.unicef_user = UserFactory(unicef_user=True)
        cls.common_user = UserFactory()
        cls.create_data = {
            'description': 'do something',
            'due_date': date.today(),
            'assigned_to': cls.pme_user.id,
            'office': cls.pme_user.profile.office.id,
            'section': SectionFactory().id,
            'partner': PartnerFactory().id,
        }

    def _test_list_view(self, user, expected_visits):
        response = self.forced_auth_req(
            'get',
            reverse('action-points:action-points-list'),
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            map(lambda x: x['id'], response.data['results']),
            map(lambda x: x.id, expected_visits)
        )

    def test_unicef_list_view(self):
        action_points = [ActionPointFactory(), ActionPointFactory()]

        self._test_list_view(self.pme_user, action_points)
        self._test_list_view(self.unicef_user, action_points)

    def test_unknown_user_list_view(self):
        ActionPointFactory()

        response = self.forced_auth_req(
            'get',
            reverse('action-points:action-points-list'),
            user=self.common_user
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pme_detail_view(self):
        action_point = ActionPointFactory(status='open')

        response = self.forced_auth_req(
            'get',
            reverse('action-points:action-points-detail', args=[action_point.id]),
            user=self.pme_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_unicef_detail_view(self):
        action_point = ActionPointFactory(status='open')

        response = self.forced_auth_req(
            'get',
            reverse('action-points:action-points-detail', args=[action_point.id]),
            user=self.unicef_user
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_unknown_user_detail_view(self):
        action_point = ActionPointFactory(status='open')

        response = self.forced_auth_req(
            'get',
            reverse('action-points:action-points-detail', args=[action_point.id]),
            user=self.common_user
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_author(self):
        response = self.forced_auth_req(
            'post',
            reverse('action-points:action-points-list'),
            data=self.create_data,
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('author', response.data)
        self.assertEqual(response.data['author']['id'], self.unicef_user.id)
        self.assertIn('assigned_by', response.data)
        self.assertEqual(response.data['assigned_by']['id'], self.unicef_user.id)

    def test_create_t2f_related(self):
        travel = TravelFactory()
        data = {'travel': travel.id}
        data.update(self.create_data)

        response = self.forced_auth_req(
            'post',
            reverse('action-points:action-points-list'),
            data=data,
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['travel'])
        self.assertEqual(response.data['travel'], travel.id)

    def test_travel_filter(self):
        travel = TravelFactory()
        ActionPointFactory()  # common action point, shouldn't appear while filtering
        ActionPointFactory(travel=travel)

        response = self.forced_auth_req(
            'get',
            reverse('action-points:action-points-list'),
            data={'travel': travel.id},
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_reassign(self):
        author = UserFactory(unicef_user=True)
        assignee = UserFactory(unicef_user=True)
        new_assignee = UserFactory(unicef_user=True)

        action_point = ActionPointFactory(status='open', author=author, assigned_by=author, assigned_to=assignee)
        self.assertEqual(action_point.history.count(), 0)

        response = self.forced_auth_req(
            'patch',
            reverse('action-points:action-points-detail', args=(action_point.id,)),
            user=assignee,
            data={
                'assigned_to': new_assignee.id
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['author']['id'], author.id)
        self.assertEqual(response.data['assigned_to']['id'], new_assignee.id)
        self.assertEqual(response.data['assigned_by']['id'], assignee.id)
        self.assertEqual(len(response.data['history']), 1)

    def test_add_comment(self):
        action_point = ActionPointFactory(status='open', comments__count=0)
        self.assertEqual(action_point.history.count(), 0)

        response = self.forced_auth_req(
            'patch',
            reverse('action-points:action-points-detail', args=(action_point.id,)),
            user=action_point.author,
            data={
                'comments': [{
                    'comment': fuzzy.FuzzyText().fuzz()
                }]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['comments']), 1)
        self.assertEqual(len(response.data['history']), 1)

    def test_list_csv(self):
        ActionPointFactory(status='open', comments__count=1)
        ActionPointFactory(status='open', comments__count=1, engagement=MicroAssessmentFactory())
        ActionPointFactory(
            status='open', comments__count=1,
            tpm_activity=TPMVisitFactory(tpm_activities__count=1).tpm_activities.first()
        )

        self._test_export(self.pme_user, 'action-points:action-points-export/csv')

    def test_single_csv(self):
        action_point = ActionPointFactory(status='open', comments__count=1, engagement=MicroAssessmentFactory())

        self._test_export(self.pme_user, 'action-points:action-points-export/csv', args=[action_point.id])


class TestActionPointsViewMetadata(ActionPointsTestCaseMixin):
    @classmethod
    def setUpTestData(cls):
        call_command('update_action_points_permissions', verbosity=0)

        cls.pme_user = UserFactory(pme=True)
        cls.unicef_user = UserFactory(unicef_user=True)
        cls.common_user = UserFactory()


class TestActionPointsListViewMetadada(TestActionPointsViewMetadata, BaseTenantTestCase):
    def _test_list_options(self, user, can_create=True, writable_fields=None):
        response = self.forced_auth_req(
            'options',
            reverse('action-points:action-points-list'),
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

    def test_unicef_list_options(self):
        # no need to check other users, pme is extended unicef with same permissions on create
        self._test_list_options(
            self.pme_user,
            writable_fields=[
                'description',
                'due_date',
                'assigned_to',
                'high_priority',

                # pme related fields
                'cp_output',
                'partner',
                'intervention',
                'location',
                'section',
                'office',

                'travel',
                'engagement',
                'tpm_activity',
            ]
        )


class TestActionPointsDetailViewMetadata(TestActionPointsViewMetadata):
    status = None

    def setUp(self):
        self.author = UserFactory(unicef_user=True)
        self.assignee = UserFactory(unicef_user=True)
        self.assigned_by = UserFactory(unicef_user=True)
        self.action_point = ActionPointFactory(status=self.status, author=self.author,
                                               assigned_by=self.assigned_by, assigned_to=self.assignee)

    def _test_detail_options(self, user, can_update=True, writable_fields=None):
        response = self.forced_auth_req(
            'options',
            reverse('action-points:action-points-detail', args=(self.action_point.id,)),
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


class TestOpenActionPointDetailViewMetadata(TestActionPointsDetailViewMetadata, BaseTenantTestCase):
    status = 'open'
    editable_fields = [
        'description',
        'due_date',
        'assigned_to',
        'high_priority',
        'comments',

        'cp_output',
        'partner',
        'intervention',
        'location',
        'section',
        'office',
    ]

    def test_pme_editable_fields(self):
        self._test_detail_options(self.pme_user, writable_fields=self.editable_fields)

    def test_unicef_editable_fields(self):
        self._test_detail_options(self.unicef_user, can_update=False)

    def test_author_editable_fields(self):
        self._test_detail_options(self.author, writable_fields=self.editable_fields)

    def test_assigned_by_editable_fields(self):
        self._test_detail_options(self.assigned_by, writable_fields=self.editable_fields)

    def test_assignee_editable_fields(self):
        self._test_detail_options(self.assignee, writable_fields=self.editable_fields)


class TestRelatedOpenActionPointDetailViewMetadata(TestOpenActionPointDetailViewMetadata):
    editable_fields = [
        'description',
        'due_date',
        'assigned_to',
        'high_priority',
        'comments',

        'section',
        'office',
    ]

    def setUp(self):
        super(TestRelatedOpenActionPointDetailViewMetadata, self).setUp()
        self.action_point.engagement = MicroAssessmentFactory()
        self.action_point.save()


class TestClosedActionPointDetailViewMetadata(TestActionPointsDetailViewMetadata, BaseTenantTestCase):
    status = 'completed'

    def test_pme_editable_fields(self):
        self._test_detail_options(self.pme_user, can_update=False)

    def test_unicef_editable_fields(self):
        self._test_detail_options(self.unicef_user, can_update=False)

    def test_author_editable_fields(self):
        self._test_detail_options(self.author, can_update=False)

    def test_assigned_by_editable_fields(self):
        self._test_detail_options(self.assigned_by, can_update=False)

    def test_assignee_editable_fields(self):
        self._test_detail_options(self.assignee, can_update=False)
