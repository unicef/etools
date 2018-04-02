from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib.auth import get_user_model

from mock import patch

from EquiTrack.tests.cases import BaseTenantTestCase
from azure_graph_api.utils import handle_record, handle_records
from users.tests.factories import GroupFactory, UserFactory


class TestClient(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.group = GroupFactory(name='UNICEF User')

    @patch('azure_graph_api.utils.handle_record')
    def test_handle_records(self, handle_function):
        handle_records({'value': range(3)})
        self.assertEqual(handle_function.call_count, 3)
        self.assertEqual(handle_function.call_args[0], (2, ))

    def test_handle_record_create(self):
        user_qs = get_user_model().objects
        user_initial_count = user_qs.count()
        self.assertEqual(user_qs.count(), user_initial_count)
        user_record = {
            'givenName': 'Joe',
            'mail': 'jdoe@unicef.org',
            'surname': 'Doe',
            'userPrincipalName': 'jdoe@unicef.org'
        }
        handle_record(user_record)
        self.assertEqual(user_qs.count(), user_initial_count + 1)

    def test_handle_record_update(self):
        UserFactory(username='jdoe@unicef.org', email='jdoe@unicef.org')
        user_qs = get_user_model().objects
        user_initial_count = user_qs.count()
        self.assertEqual(user_qs.count(), user_initial_count)
        user_record = {
            'givenName': 'Joe',
            'mail': 'jdoe@unicef.org',
            'surname': 'Doe',
            'userPrincipalName': 'jdoe@unicef.org'
        }
        handle_record(user_record)
        self.assertEqual(user_qs.count(), user_initial_count)
