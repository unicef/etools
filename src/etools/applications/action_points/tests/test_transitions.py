from django.core.management import call_command
from django.core.urlresolvers import reverse

from rest_framework import status

from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.tests.base import ActionPointsTestCaseMixin
from etools.applications.action_points.tests.factories import ActionPointFactory, UserFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.utils.permissions.tests.mixins import TransitionPermissionsTestCaseMixin


class ActionPointTransitionTestCase(ActionPointsTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_action_points_permissions', verbosity=0)

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
        super(TestActionPointsTransitionConditions, cls).setUpTestData()

        cls.pme_user = UserFactory(pme=True)

    def test_complete_without_comments(self):
        action_point = ActionPointFactory(status='open')

        response = self._do_transition(action_point, 'complete', self.pme_user)
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comments', response.data)

        action_point = self._refresh_instance(action_point)
        self.assertEquals(action_point.status, 'open')

    def test_complete_success(self):
        action_point = ActionPointFactory(status='pre_completed')

        response = self._do_transition(action_point, 'complete', self.pme_user)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        action_point = self._refresh_instance(action_point)
        self.assertEquals(action_point.status, 'completed')


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
        return super(ActionPointTransitionPermissionsTestCase, self).create_object(transition, **opts)

    def do_transition(self, obj, transition):
        return self._do_transition(obj, transition, self.user)


class PMEPermissionsForActionPointTransitionTestCase(ActionPointTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('open', 'complete'),
    ]

    @classmethod
    def setUpTestData(cls):
        super(PMEPermissionsForActionPointTransitionTestCase, cls).setUpTestData()

        cls.user = UserFactory(pme=True)
        cls.user_role = 'PME'


class UnicefUserPermissionsForActionPointTransitionTestCase(ActionPointTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = []

    @classmethod
    def setUpTestData(cls):
        super(UnicefUserPermissionsForActionPointTransitionTestCase, cls).setUpTestData()

        cls.user = UserFactory(unicef_user=True)
        cls.user_role = 'UNICEF User'


class AuthorPermissionsForActionPointTransitionTestCase(ActionPointTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = []

    @classmethod
    def setUpTestData(cls):
        super(AuthorPermissionsForActionPointTransitionTestCase, cls).setUpTestData()

        cls.user = UserFactory(unicef_user=True)
        cls.assigned_by = UserFactory(unicef_user=True)
        cls.user_role = 'Author'

    def create_object(self, transition, **kwargs):
        opts = {
            'author': self.user,
            'assigned_by': self.assigned_by
        }

        opts.update(kwargs)
        return super(AuthorPermissionsForActionPointTransitionTestCase, self).create_object(transition, **opts)


class AssignedByPermissionsForActionPointTransitionTestCase(ActionPointTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = []

    @classmethod
    def setUpTestData(cls):
        super(AssignedByPermissionsForActionPointTransitionTestCase, cls).setUpTestData()

        cls.author = UserFactory(unicef_user=True)
        cls.user = UserFactory(unicef_user=True)
        cls.user_role = 'Assigned By'

    def create_object(self, transition, **kwargs):
        opts = {
            'author': self.author,
            'assigned_by': self.user
        }

        opts.update(kwargs)
        return super(AssignedByPermissionsForActionPointTransitionTestCase, self).create_object(transition, **opts)


class AssigneePermissionsForActionPointTransitionTestCase(ActionPointTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('open', 'complete'),
    ]

    @classmethod
    def setUpTestData(cls):
        super(AssigneePermissionsForActionPointTransitionTestCase, cls).setUpTestData()

        cls.user = UserFactory(unicef_user=True)
        cls.user_role = 'Assignee'

    def create_object(self, transition, **kwargs):
        opts = {
            'assigned_to': self.user,
        }

        opts.update(kwargs)
        return super(AssigneePermissionsForActionPointTransitionTestCase, self).create_object(transition, **opts)
