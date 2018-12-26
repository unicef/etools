from django.urls import set_urlconf, reverse

from rest_framework import status

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.permissions_simplified.tests.factory import ModelWithFSMFieldFactory
from etools.applications.permissions_simplified.tests.models import SimplifiedTestModelWithFSMField
from etools.applications.permissions_simplified.tests.test_utils import TestModelsTestCaseMixin
from etools.applications.permissions2.tests.mixins import TransitionPermissionsTestCaseMixin
from etools.applications.users.tests.factories import UserFactory


class FSMModelTransitionPermissionsTestCase(TestModelsTestCaseMixin, TransitionPermissionsTestCaseMixin,
                                            BaseTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_urlconf('etools.applications.permissions_simplified.tests.urls')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        set_urlconf('')

    abstract = True
    model = SimplifiedTestModelWithFSMField
    factory = ModelWithFSMFieldFactory

    ALLOWED_TRANSITION = NotImplemented

    user = NotImplemented
    user_role = NotImplemented

    def do_transition(self, obj, transition):
        return self.forced_auth_req(
            'post',
            reverse('fsm-model-transition', args=(obj.id, transition)),
            user=self.user,
            data={}
        )

    def check_result(self, result, obj, transition):
        allowed = (obj.status, transition) in self.ALLOWED_TRANSITION
        success = result.status_code == status.HTTP_200_OK
        forbidden = result.status_code == status.HTTP_403_FORBIDDEN

        model_name = obj._meta.verbose_name

        if allowed and not success:
            return False, 'Error on {} {} {} by {}.\n{}: {}'.format(transition, obj.status, model_name, self.user_role,
                                                                    result.status_code, result.content)

        if not allowed and success:
            return False, 'Success for not allowed transition. {} can\'t {} {} {}.'.format(self.user_role, transition,
                                                                                           obj.status, model_name)

        if not allowed and not forbidden:
            return False, 'Error on {} {} {} by {}.\n{}: {}'.format(transition, obj.status, model_name, self.user_role,
                                                                    result.status_code, result.content)

        return True, ''


class AlicePermissionsTestCase(FSMModelTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('draft', 'start'),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory(first_name='Alice')
        cls.user_role = 'Alice'


class BobPermissionsTestCase(FSMModelTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = [
        ('started', 'finish'),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory(first_name='Bob')
        cls.user_role = 'Bob'


class CharliePermissionsTestCase(FSMModelTransitionPermissionsTestCase):
    ALLOWED_TRANSITION = []

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory(first_name='Charlie')
        cls.user_role = 'Charlie'


class TestTransitionsMetadataTestCase(TestModelsTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.bob = UserFactory(first_name='Bob')
        cls.alice = UserFactory(first_name='Alice')
        cls.charlie = UserFactory(first_name='Charlie')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_urlconf('etools.applications.permissions_simplified.tests.urls')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        set_urlconf('')

    def _test_allowed_actions(self, obj_status, user, actions):
        response = self.forced_auth_req(
            'options', reverse('fsm-model-detail', args=[ModelWithFSMFieldFactory(status=obj_status).id]), user=user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        action_codes = [action['code'] for action in response.data['actions']['allowed_FSM_transitions']]
        self.assertListEqual(action_codes, actions)

    def test_alice_draft_actions(self):
        self._test_allowed_actions('draft', self.alice, ['start'])

    def test_bob_draft_actions(self):
        self._test_allowed_actions('draft', self.bob, [])

    def test_alice_started_actions(self):
        self._test_allowed_actions('started', self.alice, [])

    def test_bob_started_actions(self):
        self._test_allowed_actions('started', self.bob, ['finish'])

    def test_alice_finished_actions(self):
        self._test_allowed_actions('finished', self.alice, [])

    def test_bob_finished_actions(self):
        self._test_allowed_actions('finished', self.bob, [])
