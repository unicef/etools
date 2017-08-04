# Python imports
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import datetime
from decimal import Decimal

# Django imports
from django.conf import settings

# 3rd party imports
import mock

# Project imports
from EquiTrack.factories import CountryFactory, AgreementFactory, InterventionFactory, FundsReservationHeaderFactory
from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import FastTenantTestCase
from users.models import User
from partners.models import Agreement, Intervention
import partners.tasks


def _build_country(name):
    '''Given a name (e.g. 'test1'), creates a Country object via FactoryBoy. The object is not saved to the database.
    It exists only in memory. We must be careful not to save this because creating a new Country in the database
    complicates schemas.
    '''
    country = CountryFactory.build(name='Country ' + name.title(), schema_name=name,
                                   domain_url='{}.example.com'.format(name))
    # Mock save() to prevent inadvertent database changes.
    country.save = mock.Mock()

    return country


@mock.patch('partners.tasks.logger', spec=['info', 'error'])
@mock.patch('partners.tasks.connection', spec=['set_tenant'])
class TestAgreementStatusAutomaticTransitionTask(FastTenantTestCase):
    '''Exercises the agreement_status_automatic_transition() task, including the task itself and its core function
    _make_agreement_status_automatic_transitions().
    '''
    def _assertCalls(self, mocked_function, all_expected_call_args):
        '''Given a mocked function (like mock_logger.info or mock_connection.set_tentant), asserts that the mock was
        called once for each set of call args, and with the args specified.
        all_expected_call_args should be a list of 2-tuples representing mock call_args. Each 2-tuple looks like --
            ((args), {kwargs})
        https://docs.python.org/3/library/unittest.mock.html#unittest.mock.Mock.call_args
        '''
        self.assertEqual(mocked_function.call_count, len(all_expected_call_args))

        for actual_call_args, expected_call_args in zip(mocked_function.call_args_list, all_expected_call_args):
            self.assertEqual(actual_call_args, expected_call_args)

    def setUp(self):
        try:
            self.admin_user = User.objects.get(username=settings.TASK_ADMIN_USER)
        except User.DoesNotExist:
            self.admin_user = UserFactory(username=settings.TASK_ADMIN_USER)

        # The global "country" should be excluded from processing. Create it to ensure it's ignored during this test.
        self.global_country = _build_country('Global')
        self.tenant_countries = [_build_country('test{}'.format(i)) for i in range(3)]

    # ----------
    # ----------
    # ----------    Test cases start here
    # ----------
    # ----------

    @mock.patch('partners.tasks._make_agreement_status_automatic_transitions')
    @mock.patch('partners.tasks.Country', spec='objects')
    def test_task(self, MockCountry, mock_make_agreement_status_automatic_transitions, mock_db_connection, mock_logger):
        '''Verify that the task executes once for each tenant country'''
        # We have to mock the Country model because we can't save instances to the database without creating
        # new schemas, so instead we mock the call we expect the task to make and return the value we want the
        # task to get.
        MockCountry.objects = mock.Mock(spec=['exclude'])
        MockCountry.objects.exclude = mock.Mock()
        mock_country_objects_exclude_queryset = mock.Mock(spec=['all'])
        MockCountry.objects.exclude.return_value = mock_country_objects_exclude_queryset
        mock_country_objects_exclude_queryset.all = mock.Mock(return_value=self.tenant_countries)

        mock_db_connection.set_tenant = mock.Mock()

        # I'm done mocking, it's time to call the task.
        partners.tasks.agreement_status_automatic_transition()

        self._assertCalls(MockCountry.objects.exclude, [((), {'name': 'Global'})])

        # These should have been called once for each tenant country
        self._assertCalls(mock_db_connection.set_tenant, [((country, ), {}) for country in self.tenant_countries])

        self._assertCalls(mock_make_agreement_status_automatic_transitions,
                          [((country.name, ), {}) for country in self.tenant_countries])
