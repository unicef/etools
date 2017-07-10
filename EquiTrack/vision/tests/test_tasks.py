# Python imports
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from unittest import TestCase
import datetime

# 3rd party imports
import mock

# Project imports
from EquiTrack.factories import CountryFactory
import vision.tasks
from vision.vision_data_synchronizer import VisionException


def _build_country(name):
    '''Given a name (e.g. 'test1'), creates a Country object via FactoryBoy. The object is not saved to the database.
    It exists only in memory. We must be careful not to save this because creating a new Country in the database
    complicates schemas.
    '''
    country = CountryFactory.build(name='Country ' + name.title(), schema_name=name,
                                   domain_url='{}.example.com'.format(name))
    country.vision_sync_enabled = True
    # We'll want to check vision_last_synced as part of the tests, so set it to a known value.
    country.vision_last_synced = None
    # We mock save() so we can see if it was called or not, also to prevent database changes.
    country.save = mock.Mock()

    return country


@mock.patch('vision.tasks.Country')
@mock.patch('vision.tasks.send_to_slack')
@mock.patch('vision.tasks.connection', spec=['set_tenant'])
class TestSyncTask(TestCase):
    '''Exercises the sync() task which requires a lot of mocking and some monkey patching.'''
    def setUp(self):
        # We have to monkey patch a global constant in vision.tasks. Here we ensure it gets un-monkeyed after the
        # test completes.
        self.restore_these_sync_handlers = vision.tasks.SYNC_HANDLERS

        def restore_sync_handlers():
            vision.tasks.SYNC_HANDLERS = self.restore_these_sync_handlers
        self.addCleanup(restore_sync_handlers)

        # Some tests modify the side effects of mock tenant handler classes. Ensure they get cleaned up after
        # every test.
        def clean_up_mock_tenant_handler_class_side_effects():
            for mock_handler_class in self.mock_tenant_handler_classes:
                mock_handler_class.side_effect = None
        self.addCleanup(clean_up_mock_tenant_handler_class_side_effects)

        self.public_country = _build_country('public')
        # In real life, vision_sync_enabled is not set on the public country.
        self.public_country.vision_sync_enabled = False
        self.tenant_countries = [_build_country('test{}'.format(i)) for i in range(3)]

        # Create 3 mocked sync_handlers and monkey patch tasks.SYNC_HANDLERS with the mocks. Note that in real life
        # the handlers are classes (not instances), so we have to make them behave like classes.
        mock_handler_classes = [mock.Mock(__name__='handler{}'.format(i)) for i in range(3)]
        # Make the first two global, the last a tenant handler.
        mock_handler_classes[0].GLOBAL_CALL = True
        mock_handler_classes[1].GLOBAL_CALL = True
        mock_handler_classes[2].GLOBAL_CALL = False

        self.mock_global_handler_classes = [mock_handler_class for mock_handler_class in mock_handler_classes
                                            if mock_handler_class.GLOBAL_CALL]
        self.mock_tenant_handler_classes = [mock_handler_class for mock_handler_class in mock_handler_classes
                                            if not mock_handler_class.GLOBAL_CALL]

        for i, mock_handler_class in enumerate(mock_handler_classes):
            # Each handler class should return a synchronizer instance, which we're also going to mock. We expect the
            # task to call .sync() on each synchronizer instance. Mocking the instance allows us to verify the task's
            # calls to sync() and to ensure it doesn't access any attributes on the synchronizer other than sync().
            mock_handler_class.return_value = mock.Mock(spec=['sync'])

        # Monkey patch the module's SYNC_HANDLERS.
        vision.tasks.SYNC_HANDLERS = mock_handler_classes

    def _configure_country_class_mock(self, CountryMock, tenant_countries_used=None):
        '''helper function for common config of CountryMock.
        tenant_countries_used should be a list of countries. If None, defaults to self.tenant_countries.
        '''
        if tenant_countries_used is None:
            tenant_countries_used = self.tenant_countries

        # We mock vision.tasks.Country so that we can control the .objects attribute. What we really want is control
        # over the return values from calls to Country.objects.filter() and Country.objects.get(). By passing a spec
        # we ensure that if the task changes and adds a method call (e.g. Country.objects.all()), this test will break.
        CountryMock.objects = mock.Mock(spec=['filter', 'get'])
        CountryMock.objects.filter = mock.Mock(return_value=tenant_countries_used)
        CountryMock.objects.get = mock.Mock(return_value=self.public_country)

    def _assertCountryMockCalls(self, CountryMock):
        '''Ensure sync() called Country.objects.filter() and Country.objects.get() as expected'''
        self.assertEqual(CountryMock.objects.filter.call_count, 1)
        self.assertEqual(CountryMock.objects.filter.call_args[0], ())
        self.assertEqual(CountryMock.objects.filter.call_args[1], {'vision_sync_enabled': True})

        self.assertEqual(CountryMock.objects.get.call_count, 1)
        self.assertEqual(CountryMock.objects.get.call_args[0], ())
        self.assertEqual(CountryMock.objects.get.call_args[1], {'schema_name': 'public'})

    def _assertVisionLastSynced(self, tenant_countries_used=None):
        '''Ensure sync() set vision_last_synced on countries as expected.
        tenant_countries_used should be a list of countries. If None, defaults to self.tenant_countries.
        '''
        if tenant_countries_used is None:
            tenant_countries_used = self.tenant_countries

        # vision_last_synced should not have been set on the public country
        self.assertIsNone(self.public_country.vision_last_synced)
        # ,save() should not have been called on the public country
        self.assertEqual(self.public_country.save.call_count, 0)

        for country in tenant_countries_used:
            # vision_last_synced should have been set to "now" on the tenants. Since "now" for the
            # task might be slightly different than "now" for this test, we accept any time within
            # the last 60 seconds which should be far more slack than necessary. If you prefer to
            # look for an exact value, mock vision.tasks.datetime.datetime.now() so you control what
            # it returns.
            self.assertIsInstance(country.vision_last_synced, datetime.datetime)
            delta = datetime.datetime.now() - country.vision_last_synced
            self.assertLess(delta.seconds, 60)

            # .save() should have been called with no args/kwargs on each country.
            self.assertEqual(country.save.call_count, 1)
            self.assertEqual(country.save.call_args, ((), {}))

    def _assertSlackNotified(self, mock_send_to_slack, tenant_countries_used=None):
        '''Ensure sync() sent the appropriate message to Slack.
        tenant_countries_used should be a list of countries. If None, defaults to self.tenant_countries.
        '''
        if tenant_countries_used is None:
            tenant_countries_used = self.tenant_countries

        self.assertEqual(mock_send_to_slack.call_count, 1)
        # Verify that each processed country was sent in the message. For some reason, the public
        # tenant is not listed in this message even though it was synced.
        expected_msg = 'Processed the following countries during sync: '
        expected_msg += ',\n '.join([country.name for country in tenant_countries_used])
        self.assertEqual(mock_send_to_slack.call_args[0], (expected_msg, ))
        self.assertEqual(mock_send_to_slack.call_args[1], {})

    def _assertConnectionTenantSet(self, mock_django_db_connection, tenant_countries_used=None):
        '''Ensure sync() set the DB connection schema to the appropriate tenant countries.
        tenant_countries_used should be a list of countries. If None, defaults to self.tenant_countries.
        '''
        if tenant_countries_used is None:
            tenant_countries_used = self.tenant_countries

        # Verify that the connection tenant was set once for each tenant country.
        self.assertEqual(mock_django_db_connection.set_tenant.call_count, len(tenant_countries_used))
        for call_args, country in zip(mock_django_db_connection.set_tenant.call_args_list, tenant_countries_used):
            self.assertEqual(call_args[0], (country, ))
            self.assertEqual(call_args[1], {})

    def _assertGlobalHandlersSynced(self):
        '''Verify that global handler classes were called (instantiated) and synced'''
        for handler_class in self.mock_global_handler_classes:
            # Each global handler class should have been called (instantiated) once.
            self.assertEqual(handler_class.call_count, 1)
            # Should have been called (instantiated) with one arg, no kwargs.
            self.assertEqual(handler_class.call_args[0], (self.public_country, ))
            self.assertEqual(handler_class.call_args[1], {})

            # Each synchronizer (instantiated class) has a sync() method that should have been
            # called once.
            self.assertEqual(handler_class.return_value.sync.call_count, 1)
            # Should have been called with no args and no kwargs.
            self.assertEqual(handler_class.return_value.sync.call_args, ((), {}))

    def _assertTenantHandlersSynced(self, tenant_countries_used=None):
        '''Verify that tenant handler classes were called (instantiated) and synced
        tenant_countries_used should be a list of countries. If None, defaults to self.tenant_countries.
        '''
        if tenant_countries_used is None:
            tenant_countries_used = self.tenant_countries

        n_expected_calls = len(tenant_countries_used)
        for handler_class in self.mock_tenant_handler_classes:
            self.assertEqual(handler_class.call_count, n_expected_calls)
            # Should have been called (instantiated) once with each tenant country as an argument and
            # no kwargs.
            for i, call_args in enumerate(handler_class.call_args_list):
                self.assertEqual(call_args[0], (tenant_countries_used[i], ))
                self.assertEqual(call_args[1], {})

            # Each synchronizer (instantiated class) has a sync() method that should have been called.
            self.assertEqual(handler_class.return_value.sync.call_count, n_expected_calls)
            # Should have been called with no args and no kwargs.
            for i, call_args in enumerate(handler_class.return_value.sync.call_args_list):
                self.assertEqual(call_args, ((), {}))

    def _assertLoggerMessages(self, mock_logger, tenant_countries_used=None):
        '''Verify that the expected messages were logged.
        tenant_countries_used should be a list of countries. If None, defaults to self.tenant_countries.
        '''
        if tenant_countries_used is None:
            tenant_countries_used = self.tenant_countries

        # We expect sync() to call logger.info() and logger.error(). If it doesn't call one/both of them, the
        # mock_logger won't have the corresponding attribute. Here we ensure that the mocks get created if they
        # haven't been already. That simplifies the code that follows.
        for call_name in ('info', 'error'):
            if not hasattr(mock_logger, call_name):
                setattr(mock_logger, call_name, mock.Mock())

        # There's a few ways to iterate through the list of call arguments passed to mock_logger.info() and
        # mock_logger.error(). I find that a generator is the easiest to use. logger_call_args holds a
        # calls args generator for each of info() and error().
        logger_call_args = {}

        def logger_call_args_generator(call_name):
            for call_args in getattr(mock_logger, call_name).call_args_list:
                yield call_args

        for call_name in ('info', 'error'):
            logger_call_args[call_name] = logger_call_args_generator(call_name)

        for handler_class in self.mock_global_handler_classes:
            # A before/after message should have been logged.
            call_args = logger_call_args['info'].next()
            expected_msg = 'Starting vision sync handler {} for country {}'
            expected_msg = expected_msg.format(handler_class.__name__, self.public_country.name)
            self.assertEqual(call_args[0], (expected_msg, ))
            self.assertEqual(call_args[1], {})

            call_args = logger_call_args['info'].next()
            expected_msg = "{} sync successfully".format(handler_class.__name__)
            self.assertEqual(call_args[0], (expected_msg, ))
            self.assertEqual(call_args[1], {})

        for handler_class in self.mock_tenant_handler_classes:
            for i_call_args, call_args in enumerate(handler_class.return_value.sync.call_args_list):
                self.assertEqual(call_args, ((), {}))

                # A before/after message should have been logged for each call to sync.
                call_args = logger_call_args['info'].next()
                expected_msg = 'Starting vision sync handler {} for country {}'
                expected_msg = expected_msg.format(handler_class.__name__,
                                                   tenant_countries_used[i_call_args].name)
                self.assertEqual(call_args[0], (expected_msg, ))
                self.assertEqual(call_args[1], {})

                if isinstance(handler_class.sync.side_effect, Exception):
                    # This handler's sync() raised an error which should have been logged.
                    expected_msg = "{} sync failed, Reason: {}".format(handler_class.__name__,
                                                                       str(handler_class.sync.side_effect))
                    call_args = logger_call_args['error'].next()
                else:
                    expected_msg = "{} sync successfully".format(handler_class.__name__)
                    call_args = logger_call_args['info'].next()

                self.assertEqual(call_args[0], (expected_msg, ))
                self.assertEqual(call_args[1], {})

        # There's one final call to logger.info() containing a list of the countries processed.
        call_args = logger_call_args['info'].next()
        expected_msg = 'Processed the following countries during sync: '
        expected_msg += ',\n '.join([country.name for country in tenant_countries_used])
        self.assertEqual(call_args[0], (expected_msg, ))
        self.assertEqual(call_args[1], {})

        # Verify that we've verified all of the call args to logger.info().
        with self.assertRaises(StopIteration):
            logger_call_args['info'].next()

        # Verify that we've verified all of the call args to logger.error().
        with self.assertRaises(StopIteration):
            logger_call_args['error'].next()

    # ----------
    # ----------
    # ----------    Test cases start here
    # ----------
    # ----------

    @mock.patch('vision.tasks.logger', spec=['info'])
    def test_sync_no_args_success_case(self, mock_logger, mock_django_db_connection, mock_send_to_slack, CountryMock):
        '''Exercise vision.tasks.sync() called with no args for the case where everything completes successfully'''
        self._configure_country_class_mock(CountryMock)
        # Mock connection.set_tenant() so we can verify calls to it.
        mock_django_db_connection.set_tenant = mock.Mock()

        # OK, we've mocked just about everything in sight, now call the task.
        vision.tasks.sync()

        # Assert all the things!
        self._assertCountryMockCalls(CountryMock)
        self._assertGlobalHandlersSynced()
        self._assertTenantHandlersSynced()
        self._assertConnectionTenantSet(mock_django_db_connection)
        self._assertVisionLastSynced()
        self._assertSlackNotified(mock_send_to_slack)
        self._assertLoggerMessages(mock_logger)

    @mock.patch('vision.tasks.logger', spec=['info', 'error'])
    def test_sync_no_args_error_case(self, mock_logger, mock_django_db_connection, mock_send_to_slack, CountryMock):
        '''Exercise vision.tasks.sync() called with no args for the case where a synchronizer raises an error'''
        self._configure_country_class_mock(CountryMock)

        # Create a mock 'side effect' that will fail sync on the last tenant country.
        def raise_sync_error(country):
            if country.name == self.tenant_countries[-1].name:
                self.sync = mock.Mock(side_effect=VisionException('banana'))

            return mock.DEFAULT

        self.mock_tenant_handler_classes[-1].side_effect = raise_sync_error

        # Mock connection.set_tenant() so we can verify calls to it.
        mock_django_db_connection.set_tenant = mock.Mock()

        # OK, we've mocked just about everything in sight, now call the task.
        vision.tasks.sync()

        # Assert all the things!
        self._assertCountryMockCalls(CountryMock)
        self._assertGlobalHandlersSynced()
        self._assertTenantHandlersSynced()
        self._assertConnectionTenantSet(mock_django_db_connection)
        self._assertVisionLastSynced()
        self._assertSlackNotified(mock_send_to_slack)
        self._assertLoggerMessages(mock_logger)

    @mock.patch('vision.tasks.logger', spec=['info'])
    def test_sync_with_matching_arg(self, mock_logger, mock_django_db_connection, mock_send_to_slack, CountryMock):
        '''Exercise vision.tasks.sync() called with a country name that matches 1 country.'''
        matching_country = self.tenant_countries[-1]

        self._configure_country_class_mock(CountryMock)
        # When we pass a country name to vision.tasks.sync(), it first calls Country.objects.filter() and then
        # calls .filter() again on the object returned from the first call to .filter(). This series of mocks ensures
        # sync() gets useable values from that series of calls.
        mock_country_queryset = mock.Mock(spec=['filter'])
        mock_country_queryset.filter = mock.Mock(return_value=[matching_country])
        CountryMock.objects.filter = mock.Mock(return_value=mock_country_queryset)

        # Mock connection.set_tenant() so we can verify calls to it.
        mock_django_db_connection.set_tenant = mock.Mock()

        # OK, we've mocked just about everything in sight, now call the task.
        vision.tasks.sync(matching_country.name)

        # Assert all the things!
        self._assertCountryMockCalls(CountryMock)
        self._assertGlobalHandlersSynced()
        self._assertTenantHandlersSynced([matching_country])
        self._assertConnectionTenantSet(mock_django_db_connection, [matching_country])
        self._assertVisionLastSynced([matching_country])
        self._assertSlackNotified(mock_send_to_slack, [matching_country])
        self._assertLoggerMessages(mock_logger, [matching_country])

    @mock.patch('vision.tasks.logger', spec=['info'])
    def test_sync_with_non_matching_arg(self, mock_logger, mock_django_db_connection, mock_send_to_slack, CountryMock):
        '''Exercise vision.tasks.sync() called with a country name that doesn't match any countries.'''
        self._configure_country_class_mock(CountryMock)

        # When we pass a country name to vision.tasks.sync(), it first calls Country.objects.filter() and then
        # calls .filter() again on the object returned from the first call to .filter(). This series of mocks ensures
        # sync() gets useable values from that series of calls.
        mock_country_queryset = mock.Mock(spec=['filter'])
        mock_country_queryset.filter = mock.Mock(return_value=[])
        CountryMock.objects.filter = mock.Mock(return_value=mock_country_queryset)

        # Mock connection.set_tenant() so we can verify calls to it.
        mock_django_db_connection.set_tenant = mock.Mock()

        # OK, we've mocked just about everything in sight, now call the task.
        vision.tasks.sync("this name doesn't match any countries")

        # Assert all the things!
        self._assertCountryMockCalls(CountryMock)
        self._assertGlobalHandlersSynced()
        self._assertTenantHandlersSynced([])
        self._assertConnectionTenantSet(mock_django_db_connection, [])
        self._assertVisionLastSynced([])
        self._assertSlackNotified(mock_send_to_slack, [])
        self._assertLoggerMessages(mock_logger, [])
