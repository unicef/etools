from datetime import date
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.urls import reverse

from factory import fuzzy
from rest_framework import status

from etools.applications.action_points.categories.models import Category
from etools.applications.action_points.models import ActionPoint, OperationsGroup, PME
from etools.applications.action_points.tests.base import ActionPointsTestCaseMixin
from etools.applications.action_points.tests.factories import ActionPointCategoryFactory, ActionPointFactory
from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.audit.tests.factories import MicroAssessmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.permissions import UNICEF_USER
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.psea.tests.factories import AssessmentFactory
from etools.applications.reports.tests.factories import SectionFactory
from etools.applications.t2f.tests.factories import TravelActivityFactory, TravelFactory
from etools.applications.tpm.tests.factories import TPMVisitFactory
from etools.applications.users.tests.factories import PMEUserFactory, SimpleUserFactory, UserFactory
from etools.libraries.djangolib.tests.utils import TestExportMixin


class TestActionPointViewSet(TestExportMixin, ActionPointsTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_action_points_permissions', verbosity=0)
        call_command('update_notifications')

        cls.pme_user = PMEUserFactory()
        cls.unicef_user = UserFactory()
        cls.common_user = SimpleUserFactory()
        cls.create_data = {
            'description': 'do something',
            'due_date': date.today(),
            'assigned_to': cls.pme_user.id,
            'office': cls.pme_user.profile.tenant_profile.office.id,
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
        travel_activity = TravelActivityFactory()
        data = {'travel_activity': travel_activity.id}
        data.update(self.create_data)

        response = self.forced_auth_req(
            'post',
            reverse('action-points:action-points-list'),
            data=data,
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['travel_activity'])
        self.assertEqual(response.data['travel_activity'], travel_activity.id)

    def test_create_wrong_category(self):
        data = {'category': ActionPointCategoryFactory(module=Category.MODULE_CHOICES.audit).id}
        data.update(self.create_data)

        response = self.forced_auth_req(
            'post',
            reverse('action-points:action-points-list'),
            data=data,
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', response.data)

    def test_travel_filter(self):
        travel_activity = TravelActivityFactory()
        ActionPointFactory()  # common action point, shouldn't appear while filtering
        ActionPointFactory(travel_activity=travel_activity)

        response = self.forced_auth_req(
            'get',
            reverse('action-points:action-points-list'),
            data={'travel_activity': travel_activity.id},
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_multiple_status(self):
        ActionPointFactory(status='open')
        ActionPointFactory(status='completed')

        response = self.forced_auth_req(
            'get',
            reverse('action-points:action-points-list'),
            data={'status': 'completed'},
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        response = self.forced_auth_req(
            'get',
            reverse('action-points:action-points-list'),
            data={'status__in': 'open,completed'},
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_reassign(self):
        author = UserFactory()
        assignee = UserFactory()
        new_assignee = UserFactory()

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

    def test_supporting_document_optional(self):
        action_point = ActionPointFactory(status='open', comments__count=0)

        response = self.forced_auth_req(
            'options',
            reverse('action-points:action-points-detail', args=(action_point.id,)),
            user=action_point.author
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            response.data['actions']['PUT']['comments']['child']['children']['supporting_document']['required']
        )

    def test_add_supporting_document(self):
        action_point = ActionPointFactory(status='open', comments__count=1)
        comment = action_point.comments.first()
        attachment = AttachmentFactory(file_type=None, uploaded_by=None)

        response = self.forced_auth_req(
            'patch',
            reverse('action-points:action-points-detail', args=(action_point.id,)),
            user=action_point.author,
            data={
                'comments': [{
                    'id': comment.id,
                    'supporting_document': attachment.id
                }]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document = comment.supporting_document.first()
        self.assertIsNotNone(document)
        self.assertEqual(document.id, attachment.id)
        self.assertEqual(document.uploaded_by, action_point.author)
        self.assertEqual(document.code, 'action_points_supporting_document')
        self.assertEqual(response.data['comments'][0]['supporting_document']['id'], attachment.id)

    def test_remove_supporting_document(self):
        action_point = ActionPointFactory(status='open', comments__count=1)
        comment = action_point.comments.first()
        AttachmentFactory(code='action_points_supporting_document', content_object=comment)

        response = self.forced_auth_req(
            'patch',
            reverse('action-points:action-points-detail', args=(action_point.id,)),
            user=action_point.author,
            data={
                'comments': [{
                    'id': comment.id,
                    'supporting_document': None
                }]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(comment.supporting_document.count(), 0)

    def test_add_supporting_document_permission_denied(self):
        action_point = ActionPointFactory(status='completed', comments__count=1)
        comment = action_point.comments.first()
        attachment = AttachmentFactory()

        response = self.forced_auth_req(
            'patch',
            reverse('action-points:action-points-detail', args=(action_point.id,)),
            user=action_point.author,
            data={
                'comments': [{
                    'id': comment.id,
                    'supporting_document': attachment.id
                }]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(comment.supporting_document.count(), 0)

    def test_complete(self):
        action_point = ActionPointFactory(status='pre_completed')
        self.assertEqual(action_point.history.count(), 0)
        response = self.forced_auth_req(
            'post',
            reverse('action-points:action-points-transition', args=(action_point.id, 'complete')),
            user=action_point.assigned_to,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(len(response.data['history']), 1)

    def test_update_wrong_category(self):
        action_point = ActionPointFactory(status='open', comments__count=0, engagement=MicroAssessmentFactory())

        response = self.forced_auth_req(
            'patch',
            reverse('action-points:action-points-detail', args=(action_point.id,)),
            user=action_point.author,
            data={
                'category': ActionPointCategoryFactory(module=Category.MODULE_CHOICES.apd).id
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', response.data)

    def test_update_related_category(self):
        action_point = ActionPointFactory(status='open', comments__count=0, engagement=MicroAssessmentFactory())

        response = self.forced_auth_req(
            'patch',
            reverse('action-points:action-points-detail', args=(action_point.id,)),
            user=action_point.author,
            data={
                'category': ActionPointCategoryFactory(module=Category.MODULE_CHOICES.audit).id
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_csv(self):
        ActionPointFactory(status='open', comments__count=1)
        ActionPointFactory(status='open', comments__count=1, engagement=MicroAssessmentFactory())
        ActionPointFactory(
            status='open', comments__count=1,
            tpm_activity=TPMVisitFactory(tpm_activities__count=1).tpm_activities.first()
        )
        ActionPointFactory(psea_assessment=AssessmentFactory())
        traveler = UserFactory()
        ActionPointFactory(
            status='open',
            travel_activity=TravelActivityFactory(
                primary_traveler=traveler,
                travels=[TravelFactory(traveler=traveler)]
            )
        )

        self._test_export(self.pme_user, 'action-points:action-points-list-csv-export')

    def test_list_xlsx(self):
        ActionPointFactory(status='open', comments__count=1)
        ActionPointFactory(
            status='open',
            comments__count=1,
            engagement=MicroAssessmentFactory(),
        )
        ActionPointFactory(
            status='open',
            comments__count=1,
            tpm_activity=TPMVisitFactory(
                tpm_activities__count=1
            ).tpm_activities.first(),
        )
        traveler = UserFactory()
        ActionPointFactory(
            status='open',
            travel_activity=TravelActivityFactory(
                primary_traveler=traveler,
                travels=[TravelFactory(traveler=traveler)]
            )
        )

        self._test_export(
            self.pme_user,
            'action-points:action-points-list-xlsx-export',
        )

    def test_single_csv(self):
        action_point = ActionPointFactory(status='open', comments__count=1, engagement=MicroAssessmentFactory())

        self._test_export(self.pme_user, 'action-points:action-points-single-csv-export', args=[action_point.id])

    def test_single_xlsx(self):
        action_point = ActionPointFactory(
            status='open',
            comments__count=1,
            engagement=MicroAssessmentFactory(),
        )

        self._test_export(
            self.pme_user,
            'action-points:action-points-single-xlsx-export',
            args=[action_point.id],
        )


class TestActionPointsViewMetadata(ActionPointsTestCaseMixin):
    @classmethod
    def setUpTestData(cls):
        call_command('update_action_points_permissions', verbosity=0)
        call_command('update_notifications')

        cls.pme_user = PMEUserFactory()
        cls.operations = UserFactory(realms__data=[UNICEF_USER, OperationsGroup.name])
        cls.unicef_user = UserFactory()
        cls.common_user = SimpleUserFactory()


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
                'category',
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

                'travel_activity',
                'engagement',
                'tpm_activity',
                'psea_assessment',
            ]
        )


class TestActionPointsDetailViewMetadata(TestActionPointsViewMetadata):
    status = None

    def setUp(self):
        self.author = UserFactory()
        self.assignee = UserFactory()
        self.assigned_by = UserFactory()
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
        'category',
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


class TestOpenHighPriorityActionPointDetailViewMetadata(TestOpenActionPointDetailViewMetadata):
    def setUp(self):
        super().setUp()
        self.action_point.high_priority = True
        self.action_point.save()

    def test_author_editable_fields(self):
        self._test_detail_options(self.author, writable_fields=self.editable_fields)


class TestRelatedOpenActionPointDetailViewMetadata(TestOpenActionPointDetailViewMetadata):
    editable_fields = [
        'category',
        'description',
        'due_date',
        'assigned_to',
        'high_priority',
        'comments',

        'section',
        'office',
    ]

    def setUp(self):
        super().setUp()
        self.action_point.engagement = MicroAssessmentFactory()
        self.action_point.save()


class TestClosedActionPointDetailViewMetadata(TestActionPointsDetailViewMetadata, BaseTenantTestCase):
    status = 'completed'

    def setUp(self):
        super().setUp()
        self.action_point.is_adequate = True
        self.action_point.verified_by = UserFactory()
        self.action_point.save()

    def test_pme_editable_fields(self):
        self._test_detail_options(self.pme_user, can_update=False)

    def test_operations_editable_fields(self):
        self._test_detail_options(self.operations, can_update=False)

    def test_unicef_editable_fields(self):
        self._test_detail_options(self.unicef_user, can_update=False)

    def test_author_editable_fields(self):
        self._test_detail_options(self.author, can_update=False)

    def test_assigned_by_editable_fields(self):
        self._test_detail_options(self.assigned_by, can_update=False)

    def test_assignee_editable_fields(self):
        self._test_detail_options(self.assignee, can_update=False)


class TestClosedNotVerifiedActionPointDetailViewMetadata(TestActionPointsDetailViewMetadata, BaseTenantTestCase):
    status = 'completed'

    def test_pme_editable_fields(self):
        self._test_detail_options(self.pme_user, can_update=False)

    def test_operations_editable_fields(self):
        self._test_detail_options(self.operations, can_update=False)

    def test_unicef_editable_fields(self):
        self._test_detail_options(self.unicef_user, can_update=False)

    def test_author_editable_fields(self):
        self._test_detail_options(self.author, can_update=False)

    def test_assigned_by_editable_fields(self):
        self._test_detail_options(self.assigned_by, can_update=False)

    def test_assignee_editable_fields(self):
        self._test_detail_options(self.assignee, can_update=False)


class TestHighPriorityClosedNotVerifiedActionPointDetailViewMetadata(
    TestClosedNotVerifiedActionPointDetailViewMetadata,
):
    def setUp(self):
        super().setUp()
        self.action_point.high_priority = True
        self.action_point.save()

    def test_pme_editable_fields(self):
        self._test_detail_options(self.pme_user, writable_fields=['is_adequate'])

    def test_operations_editable_fields(self):
        self._test_detail_options(self.operations, writable_fields=['is_adequate'])


class TestReviewClosedActionPoint(ActionPointsTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_action_points_permissions', verbosity=0)
        call_command('update_notifications')

        cls.pme_user = PMEUserFactory()
        cls.unicef_user = UserFactory()
        cls.common_user = SimpleUserFactory()

    def test_high_priority_author_completes(self):
        # author has PME group though it shouldn't be able to transition without providing verifier
        action_point = ActionPointFactory(
            status='pre_completed',
            high_priority=True,
            author__realms__data=[UNICEF_USER, PME.name],
        )
        reviewer = UserFactory()

        response = self.forced_auth_req(
            'options',
            reverse('action-points:action-points-detail', args=(action_point.id,)),
            user=action_point.author,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['actions']['allowed_FSM_transitions'],
            [{'code': 'complete', 'display_name': 'complete'}]
        )

        response = self.forced_auth_req(
            'post',
            reverse('action-points:action-points-transition', args=(action_point.id, 'complete')),
            user=action_point.author,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        mock_email = Mock()
        with patch("etools.applications.action_points.models.ActionPoint.send_email", mock_email):
            response = self.forced_auth_req(
                'post',
                reverse('action-points:action-points-transition', args=(action_point.id, 'complete')),
                user=action_point.author,
                data={
                    'potential_verifier': reviewer.id
                }
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        action_point = ActionPoint.objects.get(pk=action_point.pk)
        self.assertEqual(action_point.potential_verifier, reviewer)
        self.assertEqual(mock_email.call_count, 2)

    def test_high_priority_author_verifies(self):
        # author has PME group though it shouldn't be able to verify
        action_point = ActionPointFactory(
            status='completed',
            high_priority=True,
            author__realms__data=[UNICEF_USER, PME.name],
        )

        response = self.forced_auth_req(
            'patch',
            reverse('action-points:action-points-detail', args=(action_point.id,)),
            user=action_point.author,
            data={
                'is_adequate': True
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_high_priority_pme_completes_without_verifier(self):
        action_point = ActionPointFactory(status='pre_completed', high_priority=True)
        response = self.forced_auth_req(
            'post',
            reverse('action-points:action-points-transition', args=(action_point.id, 'complete')),
            user=self.pme_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_high_priority_pme_verifies(self):
        action_point = ActionPointFactory(status='completed', high_priority=True)
        response = self.forced_auth_req(
            'patch',
            reverse('action-points:action-points-detail', args=(action_point.id,)),
            user=self.pme_user,
            data={
                'is_adequate': True
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_adequate'], True)
        self.assertEqual(response.data['verified_by']['id'], self.pme_user.id)

    def test_low_priority_author_completes(self):
        action_point = ActionPointFactory(status='pre_completed', high_priority=False)
        response = self.forced_auth_req(
            'post',
            reverse('action-points:action-points-transition', args=(action_point.id, 'complete')),
            user=action_point.author,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestCategoriesViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        for module, display_value in Category.MODULE_CHOICES:
            ActionPointCategoryFactory(module=module)

    def test_list_view(self):
        response = self.forced_auth_req(
            'get',
            reverse('action-points:categories-list'),
            user=self.user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Category.objects.all().count())

    def test_list_filter(self):
        response = self.forced_auth_req(
            'get',
            reverse('action-points:categories-list'),
            user=self.user,
            data={'module': Category.MODULE_CHOICES.apd}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Category.objects.filter(module=Category.MODULE_CHOICES.apd).count())
