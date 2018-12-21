from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse, set_urlconf

from rest_framework import status

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.permissions_simplified.tests.models import SimplifiedTestParent, SimplifiedTestChild
from etools.applications.permissions_simplified.tests.test_utils import TestModelsTestCaseMixin
from etools.applications.users.tests.factories import UserFactory


class BaseTestViewSet(TestModelsTestCaseMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_urlconf('etools.applications.permissions_simplified.tests.urls')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        set_urlconf('')

    @classmethod
    def get_data(cls):
        return {}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.bob = UserFactory(first_name='Bob')
        cls.alice = UserFactory(first_name='Alice')

    def get_list_url(self):
        raise NotImplementedError

    def get_detail_url(self):
        raise NotImplementedError

    def _test_create(self, user, has_access=True):
        response = self.forced_auth_req(
            'post', self.get_list_url(),
            data=self.get_data(),
            user=user
        )

        if has_access:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        else:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_alice(self):
        self._test_create(self.alice, has_access=False)

    def test_create_bob(self):
        self._test_create(self.bob)

    def _test_list(self, user):
        response = self.forced_auth_req(
            'get', self.get_list_url(),
            user=user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_alice(self):
        self._test_list(self.alice)

    def test_list_bob(self):
        self._test_list(self.bob)

    def _test_update(self, user, has_access=True):
        response = self.forced_auth_req(
            'patch', self.get_detail_url(),
            data=self.get_data(),
            user=user
        )

        if has_access:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        else:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_alice(self):
        self._test_update(self.alice, has_access=False)

    def test_update_bob(self):
        self._test_update(self.bob)

    def _test_destroy(self, user, has_access=True):
        response = self.forced_auth_req(
            'delete', self.get_detail_url(),
            user=user
        )

        if has_access:
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        else:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_alice(self):
        self._test_destroy(self.alice, has_access=False)

    def test_destroy_bob(self):
        self._test_destroy(self.bob)

    def _test_create_metadata(self, user, has_access=True):
        response = self.forced_auth_req(
            'options', self.get_list_url(),
            user=user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if has_access:
            self.assertIn('POST', response.data['actions'])
        else:
            self.assertNotIn('POST', response.data['actions'])

    def test_create_metadata_alice(self):
        self._test_create_metadata(self.alice, has_access=False)

    def test_create_metadata_bob(self):
        self._test_create_metadata(self.bob)

    def _test_update_metadata(self, user, has_access=True):
        response = self.forced_auth_req(
            'options', self.get_detail_url(),
            user=user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if has_access:
            self.assertIn('PUT', response.data['actions'])
        else:
            self.assertNotIn('PUT', response.data['actions'])

    def test_update_metadata_alice(self):
        self._test_update_metadata(self.alice, has_access=False)

    def test_update_metadata_bob(self):
        self._test_update_metadata(self.bob)


class TestParentViewSet(BaseTestViewSet, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.instance = SimplifiedTestParent.objects.create(test_field='test')

    def get_list_url(self):
        return reverse('parents-list')

    def get_detail_url(self):
        return reverse('parents-detail', args=(self.instance.id,))

    @classmethod
    def get_data(cls):
        return {'test_field': 'test'}

    def test_create_wrong_parent(self):
        with self.assertRaises(ImproperlyConfigured):
            self.forced_auth_req(
                'post', reverse('wrong-parents-list'),
                data={'test_field': 'test'},
                user=self.alice
            )


class TestChildViewSet(BaseTestViewSet, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.parent = SimplifiedTestParent.objects.create(test_field='test')
        cls.instance = SimplifiedTestChild.objects.create(test_field='test', parent=cls.parent)

    def get_list_url(self):
        return reverse('children-list', args=(self.parent.id,))

    def get_detail_url(self):
        return reverse('children-detail', args=(self.parent.id, self.instance.id,))

    @classmethod
    def get_data(cls):
        return {'test_field': 'test', 'parent': cls.parent.id}


class TestFSMModelViewSet(TestModelsTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        set_urlconf('etools.applications.permissions_simplified.tests.urls')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        set_urlconf('')

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.bob = UserFactory(first_name='Bob')
        cls.alice = UserFactory(first_name='Alice')
        cls.charlie = UserFactory(first_name='Charlie')

    def _test_create(self, user, has_access=True):
        response = self.forced_auth_req(
            'post', reverse('fsm-model-list'),
            data={},
            user=user
        )

        if has_access:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        else:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_alice(self):
        self._test_create(self.alice)

    def test_create_bob(self):
        self._test_create(self.bob)

    def test_create_charlie(self):
        self._test_create(self.charlie, has_access=False)
