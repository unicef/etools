# Python imports
from __future__ import absolute_import, division, print_function, unicode_literals

from django.test import override_settings

import mock

from EquiTrack.tests.mixins import FastTenantTestCase
from users.models import Country
from vision.vision_data_synchronizer import VisionDataLoader, VisionDataSynchronizer
from vision.exceptions import VisionException

FAUX_VISION_URL = 'https://api.example.com/foo.svc/'
FAUX_VISION_USER = 'jane_user'
FAUX_VISION_PASSWORD = 'password123'


class TestVisionDataLoader(FastTenantTestCase):
    '''Exercise VisionDataLoader class'''
    # Note - I don't understand why, but @override_settings(VISION_URL=FAUX_VISION_URL) doesn't work when I apply
    # it on TestVisionDataLoader instead of each individual test case.

    def _assertGetFundamentals(self, url, mock_requests, mock_get_response):
        '''Assert common things about the call to loader.get()'''
        # Ensure requests.get() was called as expected
        self.assertEqual(mock_requests.get.call_count, 1)
        self.assertEqual(mock_requests.get.call_args[0], (url, ))
        self.assertEqual(mock_requests.get.call_args[1], {'headers': {'Content-Type': 'application/json'},
                                                          'auth': (FAUX_VISION_USER, FAUX_VISION_PASSWORD),
                                                          'verify': False})
        # Ensure response.json() was called as expected
        self.assertEqual(mock_get_response.json.call_count, 1)
        self.assertEqual(mock_get_response.json.call_args[0], tuple())
        self.assertEqual(mock_get_response.json.call_args[1], {})

    @override_settings(VISION_URL=FAUX_VISION_URL)
    def test_instantiation_no_country(self):
        '''Ensure I can create a loader without specifying a country'''
        loader = VisionDataLoader(endpoint='GetSomeStuff_JSON')
        self.assertEqual(loader.url, FAUX_VISION_URL + 'GetSomeStuff_JSON')

    @override_settings(VISION_URL=FAUX_VISION_URL)
    def test_instantiation_with_country(self):
        '''Ensure I can create a loader that specifies a country'''
        test_country = Country.objects.all()[0]
        test_country.business_area_code = 'ABC'
        test_country.save()

        loader = VisionDataLoader(country=test_country, endpoint='GetSomeStuff_JSON')
        self.assertEqual(loader.url, FAUX_VISION_URL + 'GetSomeStuff_JSON/ABC')

    def test_instantiation_url_construction(self):
        '''Ensure loader URL is constructed correctly regardless of whether or not base URL ends with a slash'''
        for faux_vision_url in ('https://api.example.com/foo.svc/',
                                'https://api.example.com/foo.svc'):
            with override_settings(VISION_URL=faux_vision_url):
                loader = VisionDataLoader(endpoint='GetSomeStuff_JSON')
                self.assertEqual(loader.url, 'https://api.example.com/foo.svc/GetSomeStuff_JSON')

    @override_settings(VISION_URL=FAUX_VISION_URL)
    @override_settings(VISION_USER=FAUX_VISION_USER)
    @override_settings(VISION_PASSWORD=FAUX_VISION_PASSWORD)
    @mock.patch('vision.vision_data_synchronizer.requests', spec=['get'])
    def test_get_success_with_response(self, mock_requests):
        '''Test loader.get() when the response is 200 OK and data is returned'''
        mock_get_response = mock.Mock(spec=['status_code', 'json'])
        mock_get_response.status_code = 200
        mock_get_response.json = mock.Mock(return_value=[42])
        mock_requests.get = mock.Mock(return_value=mock_get_response)

        loader = VisionDataLoader(endpoint='GetSomeStuff_JSON')
        response = loader.get()

        self._assertGetFundamentals(loader.url, mock_requests, mock_get_response)

        self.assertEqual(response, [42])

    @override_settings(VISION_URL=FAUX_VISION_URL)
    @override_settings(VISION_USER=FAUX_VISION_USER)
    @override_settings(VISION_PASSWORD=FAUX_VISION_PASSWORD)
    @mock.patch('vision.vision_data_synchronizer.requests', spec=['get'])
    def test_get_success_no_response(self, mock_requests):
        '''Test loader.get() when the response is 200 OK but no data is returned'''
        mock_get_response = mock.Mock(spec=['status_code', 'json'])
        mock_get_response.status_code = 200
        mock_get_response.json = mock.Mock(return_value='No Data Available')
        mock_requests.get = mock.Mock(return_value=mock_get_response)

        loader = VisionDataLoader(endpoint='GetSomeStuff_JSON')
        response = loader.get()

        self._assertGetFundamentals(loader.url, mock_requests, mock_get_response)

        self.assertEqual(response, [])

    @override_settings(VISION_URL=FAUX_VISION_URL)
    @override_settings(VISION_USER=FAUX_VISION_USER)
    @override_settings(VISION_PASSWORD=FAUX_VISION_PASSWORD)
    @mock.patch('vision.vision_data_synchronizer.requests', spec=['get'])
    def test_get_failure(self, mock_requests):
        '''Test loader.get() when the response is something other than 200'''
        # Note that in contrast to the other mock_get_response variables declared in this test case, this one
        # doesn't have 'json' in the spec. I don't expect the loaderto access response.json during this test, so if
        # it does this configuration ensures the test will fail.
        mock_get_response = mock.Mock(spec=['status_code'])
        mock_get_response.status_code = 401
        mock_requests.get = mock.Mock(return_value=mock_get_response)

        loader = VisionDataLoader(endpoint='GetSomeStuff_JSON')
        with self.assertRaises(VisionException) as context_manager:
            loader.get()

        # Assert that the status code is repeated in the message of the raised exception.
        self.assertIn('401', str(context_manager.exception))

        # Ensure get was called as normal.
        self.assertEqual(mock_requests.get.call_count, 1)
        self.assertEqual(mock_requests.get.call_args[0], (loader.url, ))
        self.assertEqual(mock_requests.get.call_args[1], {'headers': {'Content-Type': 'application/json'},
                                                          'auth': (FAUX_VISION_USER, FAUX_VISION_PASSWORD),
                                                          'verify': False})
