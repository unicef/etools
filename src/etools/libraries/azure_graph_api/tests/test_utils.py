
from unittest.mock import patch

from django.contrib.auth import get_user_model

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import GroupFactory, UserFactory, CountryFactory
from etools.libraries.azure_graph_api.utils import handle_record, handle_records


class TestClient(BaseTenantTestCase):
    fixtures = ['organizations']

    @classmethod
    def setUpTestData(cls):
        cls.group = GroupFactory(name='UNICEF User')

    @patch('etools.libraries.azure_graph_api.utils.handle_record',
           return_value=({'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}, {}))
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
            'userPrincipalName': 'jdoe@unicef.org',
            'userType': 'Member',
            'companyName': 'UNICEF',
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
            'userPrincipalName': 'jdoe@unicef.org',
            'userType': 'Member',
            'companyName': 'UNICEF',
        }
        handle_record(user_record)
        self.assertEqual(user_qs.count(), user_initial_count)
