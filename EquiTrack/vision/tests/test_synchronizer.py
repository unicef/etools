# Python imports
from __future__ import absolute_import, division, print_function, unicode_literals

from django.test import override_settings
from django.utils.timezone import now as django_now

import mock

from EquiTrack.tests.mixins import FastTenantTestCase
from users.models import Country
from vision.exceptions import VisionException
from vision.models import VisionSyncLog
from vision.vision_data_synchronizer import VisionDataLoader, VisionDataSynchronizer

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

    @mock.patch('vision.vision_data_synchronizer.logger.info')
    def test_sync_positive(self, mock_logger_info):
        '''Test calling sync() for the mainstream case of success. Tests the following --
            - A VisionSyncLog instance is created and has the expected values
            - # of records returned by vision can differ from the # returned by synchronizer._convert_records()
            - synchronizer._save_records() can return an int (instead of a dict)
            - The int returned by synchronizer._save_records() is recorded properly in the VisionSyncLog record
            - logger.info() is called as expected
            - All calls to synchronizer methods have expected args
        '''
        self.assertEqual(VisionSyncLog.objects.all().count(), 0)

        test_country = Country.objects.all()[0]

        synchronizer = _MySynchronizer(country=test_country)

        # These are the dummy records that vision will "return" via mock_loader.get()
        vision_records = [42, 43, 44]
        # These are the dummy records that synchronizer._convert_records() will return. It's intentionally a different
        # length than vision_records to test that these two sets of records are treated differently.
        converted_records = [42, 44]

        mock_loader = mock.Mock()
        mock_loader.get.return_value = vision_records
        MockLoaderClass = mock.Mock(return_value=mock_loader)

        synchronizer.LOADER_CLASS = MockLoaderClass

        mock_convert_records = mock.Mock(return_value=converted_records)
        synchronizer._convert_records = mock_convert_records

        # synchronizer._save_records() should logically return the # of records saved but we're going to make it
        # do something different to ensure that its return value is respected.
        mock_save_records = mock.Mock(return_value=99)
        synchronizer._save_records = mock_save_records

        # Setup is done, now call sync().
        synchronizer.sync()

        self.assertEqual(MockLoaderClass.call_count, 1)
        self.assertEqual(MockLoaderClass.call_args[0], tuple())
        self.assertEqual(MockLoaderClass.call_args[1], {'country': test_country,
                                                        'endpoint': 'GetSomeStuff_JSON'})

        self.assertEqual(mock_loader.get.call_count, 1)
        self.assertEqual(mock_loader.get.call_args[0], tuple())
        self.assertEqual(mock_loader.get.call_args[1], {})

        self.assertEqual(mock_convert_records.call_count, 1)
        self.assertEqual(mock_convert_records.call_args[0], (vision_records, ))
        self.assertEqual(mock_convert_records.call_args[1], {})

        self.assertEqual(mock_save_records.call_count, 1)
        self.assertEqual(mock_save_records.call_args[0], (converted_records, ))
        self.assertEqual(mock_save_records.call_args[1], {})

        # logger.info() is called 3 times, but the first two times are part of the instantiation of VisionDataLoader
        # and I don't care about testing them here. I only care about the last call to logger.info()
        expected_msg = 'Processing {} records'.format(len(converted_records))
        self.assertEqual(mock_logger_info.call_count, 3)
        self.assertEqual(mock_logger_info.call_args_list[2][0], (expected_msg, ))
        self.assertEqual(mock_logger_info.call_args_list[2][1], {})

        sync_logs = VisionSyncLog.objects.all()

        self.assertEqual(len(sync_logs), 1)

        sync_log = sync_logs[0]

        self.assertEqual(sync_log.country.pk, test_country.pk)
        self.assertEqual(sync_log.handler_name, '_MySynchronizer')
        self.assertEqual(sync_log.total_records, len(converted_records))
        self.assertEqual(sync_log.total_processed, 99)
        self.assertEqual(sync_log.successful, True)
        # details & exception message can be blank or None
        self.assertIn(sync_log.details, ('', None))
        self.assertIn(sync_log.exception_message, ('', None))
        # date_processed is a datetime; there's no way to know the exact microsecond it should contain. As long as
        # it's within 5 seconds of now, that's enough.
        delta = django_now() - sync_log.date_processed
        self.assertLess(delta.seconds, 5)

    def test_sync_save_records_returns_dict(self):
        '''Test calling sync() when _save_records() returns a dict. Tests that sync() provides default values
        as necessary and that values in the dict returned by _save_records() are logged.
        '''
        self.assertEqual(VisionSyncLog.objects.all().count(), 0)

        test_country = Country.objects.all()[0]

        synchronizer = _MySynchronizer(country=test_country)

        # These are the dummy records that vision will "return" via mock_loader.get()
        records = [42, 43, 44]

        mock_loader = mock.Mock()
        mock_loader.get.return_value = records
        MockLoaderClass = mock.Mock(return_value=mock_loader)

        synchronizer.LOADER_CLASS = MockLoaderClass

        mock_convert_records = mock.Mock(return_value=records)
        synchronizer._convert_records = mock_convert_records

        # I'm going to call sync() twice and test a different value from _save_records() each time.
        # The first dict is empty to prove that sync() behaves properly even when expected values are missing.
        # The second dict contains all expected values, plus an unexpected key/value pair. The extra ensures
        # sync() isn't tripped up by that.
        save_return_values = [{},
                              {'processed': 100,
                               'details': 'Hello world!',
                               'total_records': 200,
                               'foo': 'bar'}
                              ]
        mock_save_records = mock.Mock(side_effect=save_return_values)
        synchronizer._save_records = mock_save_records

        # Setup is done, now call sync().
        synchronizer.sync()

        sync_logs = VisionSyncLog.objects.all()
        self.assertEqual(len(sync_logs), 1)
        sync_log = sync_logs[0]

        self.assertEqual(sync_log.country.pk, test_country.pk)
        self.assertEqual(sync_log.handler_name, '_MySynchronizer')
        self.assertEqual(sync_log.total_records, len(records))
        self.assertEqual(sync_log.total_processed, 0)
        self.assertEqual(sync_log.successful, True)
        # details & exception message can be blank or None
        self.assertIn(sync_log.details, ('', None))
        self.assertIn(sync_log.exception_message, ('', None))
        # date_processed is a datetime; there's no way to know the exact microsecond it should contain. As long as
        # it's within 5 seconds of now, that's enough.
        delta = django_now() - sync_log.date_processed
        self.assertLess(delta.seconds, 5)

        # Get rid of this log record to simplify the remainder of the test.
        sync_log.delete()

        # Call sync again.
        synchronizer.sync()

        sync_logs = VisionSyncLog.objects.all()

        self.assertEqual(len(sync_logs), 1)

        sync_log = sync_logs[0]

        self.assertEqual(sync_log.country.pk, test_country.pk)
        self.assertEqual(sync_log.handler_name, '_MySynchronizer')
        self.assertEqual(sync_log.total_records, 200)
        self.assertEqual(sync_log.total_processed, 100)
        self.assertEqual(sync_log.successful, True)
        self.assertEqual(sync_log.details, 'Hello world!')
        # exception message can be blank or None
        self.assertIn(sync_log.exception_message, ('', None))
        # date_processed is a datetime; there's no way to know the exact microsecond it should contain. As long as
        # it's within 5 seconds of now, that's enough.
        delta = django_now() - sync_log.date_processed
        self.assertLess(delta.seconds, 5)

    def test_sync_passes_loader_kwargs(self):
        '''Test that LOADER_EXTRA_KWARGS on the synchronizer are passed to the loader.'''
        class _MyFancySynchronizer(_MySynchronizer):
            '''Synchronizer class that uses LOADER_EXTRA_KWARGS'''
            LOADER_EXTRA_KWARGS = ['FROBNICATE', 'POTRZEBIE']
            FROBNICATE = True
            POTRZEBIE = 2.2

            def _convert_records(self, records):
                return []

            def _save_records(self, records):
                return 0

        test_country = Country.objects.all()[0]

        synchronizer = _MyFancySynchronizer(country=test_country)

        mock_loader = mock.Mock()
        mock_loader.get.return_value = [42, 43, 44]
        MockLoaderClass = mock.Mock(return_value=mock_loader)

        synchronizer.LOADER_CLASS = MockLoaderClass

        # Setup is done, now call sync().
        synchronizer.sync()

        self.assertEqual(MockLoaderClass.call_count, 1)
        self.assertEqual(MockLoaderClass.call_args[0], tuple())
        self.assertEqual(MockLoaderClass.call_args[1], {'country': test_country,
                                                        'endpoint': 'GetSomeStuff_JSON',
                                                        'FROBNICATE': True,
                                                        'POTRZEBIE': 2.2})




# test LOADER_EXTRA_KWARGS passed to loader class
# test raising an exception
# Make sync logging smarter -- log the # of records received and the # converted
