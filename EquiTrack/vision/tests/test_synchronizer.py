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


class _MySynchronizer(VisionDataSynchronizer):
    '''Bare bones synchronizer class. Exists because VisionDataSynchronizer is abstract; this is concrete but
    does as little as possible.
    '''
    ENDPOINT = 'GetSomeStuff_JSON'

    def _convert_records(self, records):
        pass

    def _save_records(self, records):
        pass


class TestVisionDataLoader(FastTenantTestCase):
    '''Exercise VisionDataLoader class'''
    # Note - I don't understand why, but @override_settings(VISION_URL=FAUX_VISION_URL) doesn't work when I apply
    # it at the TestCase class level instead of each individual test case.

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


class TestVisionDataSynchronizer(FastTenantTestCase):
    '''Exercise VisionDataSynchronizer class'''
    # Note - I don't understand why, but @override_settings(VISION_URL=FAUX_VISION_URL) doesn't work when I apply
    # it at the TestCase class level instead of each individual test case.

    def test_instantiation_no_country(self):
        '''Ensure I can't create a synchronizer without specifying a country'''
        with self.assertRaises(VisionException) as context_manager:
            _MySynchronizer()

        self.assertEqual('Country is required', str(context_manager.exception))

    def test_instantiation_no_endpoint(self):
        '''Ensure I can't create a synchronizer without specifying an endpoint'''
        class _MyBadSynchronizer(_MySynchronizer):
            '''Synchronizer class that doesn't set self.ENDPOINT'''
            ENDPOINT = None

        test_country = Country.objects.all()[0]

        with self.assertRaises(VisionException) as context_manager:
            _MyBadSynchronizer(country=test_country)

        self.assertEqual('You must set the ENDPOINT name', str(context_manager.exception))

    @mock.patch('vision.vision_data_synchronizer.connection', spec=['set_tenant'])
    @mock.patch('vision.vision_data_synchronizer.logger.info')
    def test_instantiation_positive(self, mock_logger_info, mock_connection):
        '''Exercise successfully creating a synchronizer'''
        test_country = Country.objects.all()[0]
        test_country.business_area_code = 'ABC'
        test_country.save()

        _MySynchronizer(country=test_country)

        # Ensure tenant is set
        self.assertEqual(mock_connection.set_tenant.call_count, 1)
        self.assertEqual(mock_connection.set_tenant.call_args[0], (test_country, ))
        self.assertEqual(mock_connection.set_tenant.call_args[1], {})

        # Ensure msgs are logged
        self.assertEqual(mock_logger_info.call_count, 2)
        expected_msg = 'Synchronizer is _MySynchronizer'
        self.assertEqual(mock_logger_info.call_args_list[0][0], (expected_msg, ))
        self.assertEqual(mock_logger_info.call_args_list[0][1], {})

        expected_msg = 'Country is ' + test_country.name
        self.assertEqual(mock_logger_info.call_args_list[1][0], (expected_msg, ))
        self.assertEqual(mock_logger_info.call_args_list[1][1], {})
