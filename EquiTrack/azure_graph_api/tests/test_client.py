from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.test import TestCase

import responses
from azure.common import AzureHttpError
from azure_graph_api.client import azure_sync_users, get_token
from mock import patch


class TestClient(TestCase):

    @responses.activate
    def test_get_token_ok(self):
        responses.add(
            responses.POST, settings.AZURE_TOKEN_URL,
            json={'access_token': 't0k3n'}, status=200
        )
        token = get_token()
        assert token == 't0k3n'

    @responses.activate
    def test_get_token_ko(self):
        responses.add(
            responses.POST, settings.AZURE_TOKEN_URL,
            json={'access_token': 't0k3n'}, status=300
        )
        with self.assertRaises(AzureHttpError):
            get_token()

    @responses.activate
    @patch('azure_graph_api.client.get_token', return_value='t0k3n')
    @patch("azure_graph_api.client.handle_records")
    def test_azure_sync_users_ok(self, handle_function, token):
        url = '{}/{}/users?$top={}'.format(
            settings.AZURE_GRAPH_API_BASE_URL,
            settings.AZURE_GRAPH_API_VERSION,
            settings.AZURE_GRAPH_API_PAGE_SIZE
        )
        responses.add(
            responses.GET, url, status=200,
            json={'@odata.deltaLink': 'delta'},
        )
        delta = azure_sync_users(url)
        self.assertEquals(delta, 'delta')
        self.assertEqual(token.call_count, 1)
        self.assertEqual(token.call_args[0], ())
        self.assertEqual(handle_function.call_count, 1)
        self.assertEqual(handle_function.call_args[0], ({'@odata.deltaLink': 'delta'}, ))

    @responses.activate
    @patch('azure_graph_api.client.get_token', return_value='t0k3n')
    def test_azure_sync_users_ko(self, token):
        url = '{}/{}/users?$top={}'.format(
            settings.AZURE_GRAPH_API_BASE_URL,
            settings.AZURE_GRAPH_API_VERSION,
            settings.AZURE_GRAPH_API_PAGE_SIZE
        )
        responses.add(
            responses.GET, url, status=300,
            json={},
        )
        with self.assertRaises(AzureHttpError):
            azure_sync_users(url)
        self.assertEqual(token.call_count, 1)
        self.assertEqual(token.call_args[0], ())
