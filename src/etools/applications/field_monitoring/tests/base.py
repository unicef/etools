from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.libraries.djangolib.models import GroupWrapper


class FMBaseTestCaseMixin(object):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        GroupWrapper.invalidate_instances()

        cls.unicef_user = UserFactory(first_name='UNICEF User', unicef_user=True, is_staff=True)
        cls.fm_user = UserFactory(first_name='Field Monitoring User', fm_user=True, is_staff=True)
        cls.pme = UserFactory(first_name='PME User', pme=True, is_staff=True)
        cls.usual_user = UserFactory(first_name='Unknown user')


class APIViewSetTestCase(BaseTenantTestCase):
    base_view = ''

    def get_list_args(self):
        return []

    def get_detail_args(self, instance):
        return self.get_list_args() + [instance.pk]

    def get_action_url(self, action, instance=None):
        url_args = self.get_detail_args(instance) if instance else self.get_list_args()
        return reverse('{}-{}'.format(self.base_view, action), args=url_args)

    def get_list_url(self):
        return self.get_action_url('list')

    def get_detail_url(self, instance):
        return self.get_action_url('detail', instance=instance)

    def make_request_to_viewset(self, user, method='get', instance=None, action=None, data=None, **kwargs):
        if action:
            url = self.get_action_url(action, instance=instance)
        else:
            url = self.get_detail_url(instance) if instance else self.get_list_url()

        return self.forced_auth_req(method, url, user=user, data=data, **kwargs)

    def make_list_request(self, user, **kwargs):
        return self.make_request_to_viewset(user, **kwargs)

    def make_detail_request(self, user, instance, **kwargs):
        return self.make_request_to_viewset(user, instance=instance, **kwargs)

    def _test_list(self, user, expected_objects=None, expected_status=status.HTTP_200_OK, data=None):
        response = self.make_list_request(user, data=data)

        self.assertEqual(response.status_code, expected_status)

        if expected_status == status.HTTP_200_OK:
            if isinstance(response.data, dict) and 'results' in response.data:
                actual_ids = sorted(obj['id'] for obj in response.data['results'])
            else:
                actual_ids = sorted(obj['id'] for obj in response.data)

            expected_ids = sorted(obj.id for obj in (expected_objects or []))

            self.assertListEqual(actual_ids, expected_ids)

        return response

    def _test_create(self, user, data, expected_status=status.HTTP_201_CREATED, field_errors=None, **kwargs):
        response = self.make_list_request(user, method='post', data=data, **kwargs)

        self.assertEqual(response.status_code, expected_status)

        if field_errors:
            self.assertListEqual(list(response.data.keys()), field_errors)

        return response

    def _test_retrieve(self, user, instance, expected_status=status.HTTP_200_OK, field_errors=None):
        response = self.make_detail_request(user, instance)

        self.assertEqual(response.status_code, expected_status)

        if field_errors:
            self.assertListEqual(list(response.data.keys()), field_errors)

        return response

    def _test_update(self, user, instance, data, expected_status=status.HTTP_200_OK,
                     field_errors=None, basic_errors=None):
        response = self.make_detail_request(user, instance=instance, method='patch', data=data)

        self.assertEqual(response.status_code, expected_status,
                         'Unexpected status: {}. Response: {}'.format(response.status_code, response.data))

        if field_errors:
            self.assertListEqual(list(response.data.keys()), field_errors)

        if basic_errors:
            self.assertListEqual(list(map(str, response.data)), basic_errors)

        return response

    def _test_destroy(self, user, instance, expected_status=status.HTTP_204_NO_CONTENT):
        response = self.make_detail_request(user, instance, method='delete')

        self.assertEqual(response.status_code, expected_status)

        return response
