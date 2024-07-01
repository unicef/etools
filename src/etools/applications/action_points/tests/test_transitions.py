from django.core.management import call_command
from django.urls import reverse

from rest_framework import status

from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.tests.base import ActionPointsTestCaseMixin
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.permissions2.tests.mixins import TransitionPermissionsTestCaseMixin
from etools.applications.users.tests.factories import PMEUserFactory, UserFactory


class ActionPointTransitionTestCase(ActionPointsTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_action_points_permissions', verbosity=0)
        call_command('update_notifications')

    def _do_transition(self, action_point, action, user, data=None):
        data = data or {}
        return self.forced_auth_req(
            'post',
            reverse('action-points:action-points-transition', args=(action_point.id, action)),
            user=user,
            data=data
        )

    def _refresh_instance(self, instance):
        # Calling refresh_from_db will cause an exception.
        return instance.__class__.objects.get(id=instance.id)


class TestActionPointsTransitionConditions(ActionPointTransitionTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.pme_user = PMEUserFactory()

    def test_complete_without_comments(self):
        action_point = ActionPointFactory(status='open')

        response = self._do_transition(action_point, 'complete', self.pme_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comments', response.data)

        action_point = self._refresh_instance(action_point)
        self.assertEqual(action_point.status, 'open')

    def test_complete_success(self):
        action_point = ActionPointFactory(status='pre_completed')

        response = self._do_transition(action_point, 'complete', self.pme_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        action_point = self._refresh_instance(action_point)
        self.assertEqual(action_point.status, 'completed')


class ActionPointTransitionPermissionsTestCase(TransitionPermissionsTestCaseMixin, ActionPointTransitionTestCase):
    abstract = True
    model = ActionPoint
    factory = ActionPointFactory

    ALLOWED_TRANSITION = NotImplemented

    user = NotImplemented
    user_role = NotImplemented

    def create_object(self, transition, **kwargs):
        opts = {}

        if transition == 'complete':
            opts['comments__count'] = 3

        opts.update(kwargs)
        return super().create_object(transition, **opts)

    def do_transition(self, obj, transition):
        return self._do_transition(obj, transition, self.user)


class PMEPermissionsForActionPointTransitionTestCase(ActionPointTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('open', 'complete'),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = PMEUserFactory()
        cls.user_role = 'PME'


class UnicefUserPermissionsForActionPointTransitionTestCase(ActionPointTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = []

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory()
        cls.user_role = 'UNICEF User'


class AuthorPermissionsForActionPointTransitionTestCase(ActionPointTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('open', 'complete'),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory()
        cls.assigned_by = UserFactory()
        cls.user_role = 'Author'

    def create_object(self, transition, **kwargs):
        opts = {
            'author': self.user,
            'assigned_by': self.assigned_by
        }

        opts.update(kwargs)
        return super().create_object(transition, **opts)


class AssignedByPermissionsForActionPointTransitionTestCase(ActionPointTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('open', 'complete'),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.author = UserFactory()
        cls.user = UserFactory()
        cls.user_role = 'Assigned By'

    def create_object(self, transition, **kwargs):
        opts = {
            'author': self.author,
            'assigned_by': self.user
        }

        opts.update(kwargs)
        return super().create_object(transition, **opts)


class AssigneePermissionsForActionPointTransitionTestCase(ActionPointTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('open', 'complete'),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory()
        cls.user_role = 'Assignee'

    def create_object(self, transition, **kwargs):
        opts = {
            'assigned_to': self.user,
        }

        opts.update(kwargs)
        return super().create_object(transition, **opts)
