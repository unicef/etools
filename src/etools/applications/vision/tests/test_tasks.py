# Python imports

import datetime

from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.utils import timezone

import mock
from unicef_vision.exceptions import VisionException

import etools.applications.vision.tasks
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import CountryFactory


def _build_country(name):
    """
    Given a name (e.g. 'test1'), creates a Country object via FactoryBoy. The object is not saved to the database.
    It exists only in memory. We must be careful not to save this because creating a new Country in the database
    complicates schemas.
    """
    country = CountryFactory.build(name='Country {}'.format(name.title()),
                                   schema_name=name,
                                   business_area_code='ZZZ {}'.format(name.title()))
    country.vision_sync_enabled = True
    # We'll want to check vision_last_synced as part of the tests, so set it to a known value.
    country.vision_last_synced = None
    # We mock save() so we can see if it was called or not, also to prevent database changes.
    country.save = mock.Mock()

    return country


@mock.patch('etools.applications.vision.tasks.Country')
@mock.patch('etools.applications.vision.tasks.send_to_slack')
@mock.patch('etools.applications.vision.tasks.sync_handler')
@mock.patch('etools.applications.vision.tasks.connection', spec=['set_tenant'])
@mock.patch('etools.applications.vision.tasks.logger.info')
class TestVisionSyncTask(SimpleTestCase):
    """Exercises the vision_sync_task() task which requires a lot of mocking and some monkey patching."""

    def setUp(self):
        super().setUp()
        self.public_country = _build_country('Global')
        # Vision_sync_enabled is not set on the public country.
        self.public_country.vision_sync_enabled = False
        self.tenant_countries = [_build_country('test{}'.format(i)) for i in range(3)]

    def _assertCountryMockCalls(self, countryMock):
        """Ensure vision_sync_task() called Country.objects.filter()"""
        self.assertEqual(countryMock.objects.filter.call_count, 1)

    def _assertVisionLastSynced(self, tenant_countries_used=None):
        """Ensure vision_sync_task() set vision_last_synced on countries as expected.
        tenant_countries_used should be a list of countries. If None, defaults to self.tenant_countries.
        """
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
            # look for an exact value, mock etools.applications.vision.tasks.timezone.now() so you control what
            # it returns.
            self.assertIsInstance(country.vision_last_synced, datetime.datetime)
            delta = timezone.now() - country.vision_last_synced
            self.assertLess(delta.seconds, 60)

            # .save() should have been called with no args/kwargs on each country.
            self.assertEqual(country.save.call_count, 1)
            self.assertEqual(country.save.call_args, ((), {}))

    def _assertSlackNotified(self, mock_send_to_slack, tenant_countries_used=None, selected_synchronizers=None):
        """Ensure vision_sync_task() sent the appropriate message to Slack.
        tenant_countries_used should be a list of countries. If None, defaults to self.tenant_countries.
        selected_synchronizers should be a list of synchronizers. If None, SYNC_HANDLERS is used.
        """
        if tenant_countries_used is None:
            tenant_countries_used = self.tenant_countries
        if not selected_synchronizers:
            selected_synchronizers = etools.applications.vision.tasks.SYNC_HANDLERS.keys()

        self.assertEqual(mock_send_to_slack.call_count, 1)
        # Verify that each processed country was sent in the message. For some reason, the public
        # tenant is not listed in this message even though it was synced.
        expected_msg = 'Created tasks for the following countries: {} and synchronizers: {}'.format(
            ',\n '.join([country.name for country in tenant_countries_used]),
            ',\n '.join([synchronizer for synchronizer in selected_synchronizers])
        )
        self.assertEqual(mock_send_to_slack.call_args[0], (expected_msg, ))
        self.assertEqual(mock_send_to_slack.call_args[1], {})

    def _assertConnectionTenantSet(self, mock_django_db_connection, tenant_countries_used=None):
        """Ensure vision_sync_task() set the DB connection schema to the appropriate tenant countries.
        tenant_countries_used should be a list of countries. If None, defaults to self.tenant_countries.
        """
        if tenant_countries_used is None:
            tenant_countries_used = self.tenant_countries

        # Verify that the connection tenant was set once for each tenant country.
        self.assertEqual(mock_django_db_connection.set_tenant.call_count, len(tenant_countries_used))
        for call_args, country in zip(mock_django_db_connection.set_tenant.call_args_list, tenant_countries_used):
            self.assertEqual(call_args[0], (country, ))
            self.assertEqual(call_args[1], {})

    def _assertGlobalHandlersSynced(self, mock_handler, all_sync_task=15, public_task=0):
        """Verify that public handler tasks were called
        all_sync_task is the number of tasks called.
        sync_t0 is the number of tasks called for public schema
        """
        self.assertEqual(mock_handler.delay.call_count, all_sync_task)
        countries = [arguments[0][0] for arguments in mock_handler.delay.call_args_list]
        self.assertEqual(countries.count('Global'), public_task)

    def _assertTenantHandlersSynced(self, mock_handler, all_sync_task=15, sync_t0=5, sync_t1=5, sync_t2=5):
        """Verify that tenant handler tasks were called
        all_sync_task is the number of tasks called.
        sync_t0 is the number of tasks called for ZZZ Test 0
        sync_t1 is the number of tasks called for ZZZ Test 1
        sync_t2 is the number of tasks called for ZZZ Test 2
        """
        self.assertEqual(mock_handler.delay.call_count, all_sync_task)
        countries = [arguments[0][0] for arguments in mock_handler.delay.call_args_list]
        self.assertEqual(countries.count('ZZZ Test0'), sync_t0)
        self.assertEqual(countries.count('ZZZ Test1'), sync_t1)
        self.assertEqual(countries.count('ZZZ Test2'), sync_t2)

    def _assertLoggerMessages(self, mock_logger, tenant_countries_used=None, selected_synchronizers=None):
        """Ensure the task sent the appropriate message to Slack.
        tenant_countries_used should be a list of countries. If None, defaults to self.tenant_countries.
        selected_synchronizers should be a list of synchronizers. If None, SYNC_HANDLERS is used.
        """
        if tenant_countries_used is None:
            tenant_countries_used = self.tenant_countries
        if not selected_synchronizers:
            selected_synchronizers = etools.applications.vision.tasks.SYNC_HANDLERS.keys()

        self.assertEqual(mock_logger.call_count, 1)
        # Verify that each processed country was sent in the message. For some reason, the public
        # tenant is not listed in this message even though it was synced.
        expected_msg = 'Created tasks for the following countries: {} and synchronizers: {}'.format(
            ',\n '.join([country.name for country in tenant_countries_used]),
            ',\n '.join([synchronizer for synchronizer in selected_synchronizers])
        )
        self.assertEqual(mock_logger.call_args[0], (expected_msg, ))
        self.assertEqual(mock_logger.call_args[1], {})

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_sync_no_args_success_case(self, mock_logger, mock_django_db_connection, mock_handler, mock_send_to_slack,
                                       countryMock):
        """Exercise etools.applications.vision.tasks.vision_sync_task() called without passing any argument"""

        countryMock.objects.filter = mock.Mock(return_value=self.tenant_countries)
        # Mock connection.set_tenant() so we can verify calls to it.
        mock_django_db_connection.set_tenant = mock.Mock()
        etools.applications.vision.tasks.vision_sync_task()

        self._assertCountryMockCalls(countryMock)
        self._assertGlobalHandlersSynced(mock_handler, 18)
        self._assertTenantHandlersSynced(mock_handler, 18, 6, 6, 6)
        self._assertConnectionTenantSet(mock_django_db_connection)
        self._assertVisionLastSynced()
        self._assertSlackNotified(mock_send_to_slack)
        self._assertLoggerMessages(mock_logger)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_sync_country_filter_args(self, mock_logger, mock_django_db_connection, mock_handler, mock_send_to_slack,
                                      countryMock):
        """
        Exercise etools.applications.vision.tasks.vision_sync_task() called with passing as argument a specific country
        """

        selected_countries = [self.tenant_countries[0], ]
        countryMock.objects.filter = mock.Mock(return_value=selected_countries)
        mock_django_db_connection.set_tenant = mock.Mock()
        etools.applications.vision.tasks.vision_sync_task(business_area_code='ZZZ Test0')

        self._assertCountryMockCalls(countryMock)
        self._assertGlobalHandlersSynced(mock_handler, all_sync_task=6)
        self._assertTenantHandlersSynced(mock_handler, 6, 6, 0, 0)
        self._assertConnectionTenantSet(mock_django_db_connection, selected_countries)
        self._assertVisionLastSynced(selected_countries)
        self._assertSlackNotified(mock_send_to_slack, selected_countries)
        self._assertLoggerMessages(mock_logger, selected_countries)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_sync_synchronizer_filter_args(self, mock_logger, mock_django_db_connection, mock_handler,
                                           mock_send_to_slack, countryMock):
        """
        Exercise etools.applications.vision.tasks.vision_sync_task()
        called with passing as argument a specific synchronizer
        """
        selected_synchronizers = ['programme', ]
        countryMock.objects.filter = mock.Mock(return_value=self.tenant_countries)
        # Mock connection.set_tenant() so we can verify calls to it.
        mock_django_db_connection.set_tenant = mock.Mock()
        etools.applications.vision.tasks.vision_sync_task(synchronizers=selected_synchronizers)

        self._assertCountryMockCalls(countryMock)
        self._assertGlobalHandlersSynced(mock_handler, all_sync_task=3, public_task=0)
        self._assertTenantHandlersSynced(mock_handler, all_sync_task=3, sync_t0=1, sync_t1=1, sync_t2=1)
        self._assertConnectionTenantSet(mock_django_db_connection)
        self._assertVisionLastSynced()
        self._assertSlackNotified(mock_send_to_slack, None, selected_synchronizers)
        self._assertLoggerMessages(mock_logger, None, selected_synchronizers)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_sync_country_and_synchronizer_filter_args(self, mock_logger, mock_django_db_connection, mock_handler,
                                                       mock_send_to_slack, countryMock):
        """
        Exercise etools.applications.vision.tasks.vision_sync_task()
        called with passing a specific country and a synchronizer
        """
        selected_synchronizers = ['programme', ]
        selected_countries = [self.tenant_countries[0], ]

        countryMock.objects.filter = mock.Mock(return_value=selected_countries)
        # Mock connection.set_tenant() so we can verify calls to it.
        mock_django_db_connection.set_tenant = mock.Mock()
        etools.applications.vision.tasks.vision_sync_task(
            business_area_code='ZZZ Test0', synchronizers=selected_synchronizers)

        self._assertCountryMockCalls(countryMock)
        self._assertGlobalHandlersSynced(mock_handler, all_sync_task=1, public_task=0)
        self._assertTenantHandlersSynced(mock_handler, all_sync_task=1, sync_t0=1, sync_t1=0, sync_t2=0)
        self._assertConnectionTenantSet(mock_django_db_connection, selected_countries)
        self._assertVisionLastSynced(selected_countries)
        self._assertSlackNotified(mock_send_to_slack, selected_countries, selected_synchronizers)
        self._assertLoggerMessages(mock_logger, selected_countries, selected_synchronizers)


class TestSyncHandlerTask(BaseTenantTestCase):
    """Exercises the sync_handler()"""

    def setUp(self):
        self.country = _build_country('My')

    @mock.patch('etools.applications.vision.tasks.logger.info')
    @mock.patch('etools.applications.vision.tasks.Country')
    @mock.patch('etools.applications.vision.tasks.ProgrammeSynchronizer.sync')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_sync_success(self, Handler, Country, mock_logger_info):
        """Exercise etools.applications.vision.tasks.sync_handler() success scenario, one matching country."""
        Country.objects.get = mock.Mock(return_value=self.country)

        etools.applications.vision.tasks.sync_handler.delay(self.country.business_area_code, 'programme')
        self.assertEqual(mock_logger_info.call_count, 1)
        expected_msg = 'Starting vision sync handler {} for country {}'.format(
            'programme', 'ZZZ My'
        )
        self.assertEqual(mock_logger_info.call_args[0], (expected_msg,))
        self.assertEqual(mock_logger_info.call_args[1], {})

    @mock.patch('etools.applications.vision.tasks.logger.info')
    @mock.patch('etools.applications.vision.tasks.logger.error')
    @mock.patch('etools.applications.vision.tasks.Country')
    @mock.patch('etools.applications.vision.tasks.ProgrammeSynchronizer.sync', side_effect=VisionException('banana'))
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=False)
    def test_sync_vision_error(self, Handler, Country, mock_logger_error, mock_logger_info):
        """Exercise etools.applications.vision.tasks.sync_handler() which receive an exception from Vision."""
        Country.objects.get = mock.Mock(return_value=self.country)

        etools.applications.vision.tasks.sync_handler.delay(self.country.business_area_code, 'programme')
        # Check that it got retried once
        self.assertEqual(mock_logger_info.call_count, 1)
        self.assertEqual(mock_logger_error.call_count, 0)
        expected_msg = 'Starting vision sync handler {} for country {}'.format(
            'programme', 'ZZZ My'
        )
        self.assertEqual(mock_logger_info.call_args[0], (expected_msg,))
        self.assertEqual(mock_logger_info.call_args[1], {})

    @mock.patch('etools.applications.vision.tasks.logger.error')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_sync_country_does_not_exist(self, mock_logger):
        """
        Exercise etools.applications.vision.tasks.sync_handler() called with a country name that doesn't match a country
        """
        etools.applications.vision.tasks.sync_handler.delay('random', 'programme')
        self.assertEqual(mock_logger.call_count, 1)
        expected_msg = '{} sync failed, Could not find a Country with this business area code: {}'.format(
            'programme', 'random'
        )
        self.assertEqual(mock_logger.call_args[0], (expected_msg,))
        self.assertEqual(mock_logger.call_args[1], {})
