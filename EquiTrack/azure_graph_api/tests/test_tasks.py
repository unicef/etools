from __future__ import absolute_import, division, print_function, unicode_literals

from django.test import TestCase

from azure_graph_api.tasks import sync_all_users, sync_delta_users, sync_user
from mock import patch


class TestTasks(TestCase):

    @patch('azure_graph_api.tasks.azure_sync_users')
    def test_sync_user(self, handle_function):
        sync_user('jdoe@unicef.org')
        self.assertEqual(handle_function.call_count, 1)
        self.assertEqual(handle_function.call_args[0], ('https://graph.microsoft.com/beta/users/jdoe@unicef.org', ))

    @patch('azure_graph_api.tasks.azure_sync_users')
    def test_sync_all_users(self, handle_function):
        sync_all_users()
        self.assertEqual(handle_function.call_count, 1)
        self.assertEqual(handle_function.call_args[0], ('https://graph.microsoft.com/beta/users?$top=250',))

    @patch('azure_graph_api.tasks.azure_sync_users', return_value='delta')
    def test_sync_delta_users(self, handle_function):
        delta = sync_delta_users()
        self.assertEqual(delta, 'delta')
        self.assertEqual(handle_function.call_count, 1)
        self.assertEqual(handle_function.call_args[0], ('https://graph.microsoft.com/beta/users/delta?$top=250',))
