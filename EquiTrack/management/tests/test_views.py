from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.urlresolvers import reverse

from mock import patch
from rest_framework import status

from EquiTrack.tests.mixins import APITenantTestCase
from users.tests.factories import CountryFactory, UserFactory


class InvalidateCacheTest(APITenantTestCase):

    def setUp(self):
        self.staff_user = UserFactory(is_staff=True)
        self.superuser = UserFactory(is_superuser=True)
        self.url = reverse('management:invalidate_cache')

    def test_not_superuser(self):
        """
        Only superusers are allowed to use this view.
        """
        response = self.forced_auth_req('get', self.url, user=self.staff_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_key(self):
        """
        If key is not provided, return an error message.
        """
        response = self.forced_auth_req('get', self.url, user=self.superuser)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'You must pass "key" as a query param')

    @patch('management.views.general.cache')
    def test_valid_key(self, mock_cache):
        """
        If key is provided, return 200 success message and call cache API to delete key.
        """
        cache_key_to_delete = 'delete-me'
        request_data = {
            'key': cache_key_to_delete,
        }
        response = self.forced_auth_req('get', self.url, user=self.superuser, data=request_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], 'key removed if it was present')
        # assert that cache.delete() was called properly
        mock_cache.delete.assert_called_with(cache_key_to_delete)


class LoadResultStructureTest(APITenantTestCase):

    def setUp(self):
        self.staff_user = UserFactory(is_staff=True)
        self.superuser = UserFactory(is_superuser=True)
        self.url = reverse('management:load_result_structure')

    def test_not_superuser(self):
        """
        Only superusers are allowed to use this view.
        """
        response = self.forced_auth_req('get', self.url, user=self.staff_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_country(self):
        """
        Return 400 if no country supplied.
        """
        response = self.forced_auth_req('get', self.url, user=self.superuser)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Country not found')

    def test_bad_country(self):
        """
        Return 400 if country not found in our database.
        """
        request_data = {
            'country': 'Bad Country',
        }
        response = self.forced_auth_req('get', self.url, user=self.superuser, data=request_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Country not found')

    @patch('management.views.reports.ProgrammeSynchronizer')
    def test_good_country(self, mock_synchronizer):
        """
        Sync country and return success response.
        """
        country = CountryFactory()
        request_data = {
            'country': country.name,
        }
        response = self.forced_auth_req('get', self.url, user=self.superuser, data=request_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], 'Country = {}'.format(country.name))
        # assert that sync was called
        mock_synchronizer.return_value.sync.assert_called()

    @patch('management.views.reports.ProgrammeSynchronizer')
    def test_good_country_sync_error(self, mock_synchronizer):
        """
        If Synchronizer throws an error, then return 500.
        """
        country = CountryFactory()
        request_data = {
            'country': country.name,
        }
        mock_synchronizer.return_value.sync.side_effect = Exception
        response = self.forced_auth_req('get', self.url, user=self.superuser, data=request_data)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
