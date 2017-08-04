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

    def test_make_agreement_status_automatic_transitions_no_agreements(self, mock_db_connection, mock_logger):
        '''Exercise _make_agreement_status_automatic_transitions() for the simple case when there's no agreements.'''
        # Don't need to mock anything extra, just call the function.
        partners.tasks._make_agreement_status_automatic_transitions(self.tenant_countries[0].name)

        # Verify logged messages.
        expected_call_args = [
            (('Starting agreement auto status transition for country {}'.format(self.tenant_countries[0].name), ), {}),
            (('Total agreements 0', ), {}),
            (('Transitioned agreements 0 ', ), {}),
            ]
        self._assertCalls(mock_logger.info, expected_call_args)

        expected_call_args = [
            (('Bad agreements 0', ), {}),
            (('Bad agreements ids: ', ), {}),
            ]
        self._assertCalls(mock_logger.error, expected_call_args)

    @mock.patch('partners.tasks.AgreementValid')
    def test_make_agreement_status_automatic_transitions_with_valid_agreements(
            self,
            MockAgreementValid,
            mock_db_connection,
            mock_logger):
        '''Exercise _make_agreement_status_automatic_transitions() when all agreements are valid.'''
        end_date = datetime.date.today() + datetime.timedelta(days=2)
        agreements = [AgreementFactory(status=Agreement.SIGNED, end=end_date, agreement_type=Agreement.MOU)
                      for i in range(3)]

        # Create a few items that should be ignored. If they're not ignored, this test will fail.
        AgreementFactory(status=Agreement.SUSPENDED, end=end_date, agreement_type=Agreement.MOU)
        AgreementFactory(status=Agreement.SIGNED,
                         end=datetime.date.today() - datetime.timedelta(days=2),
                         agreement_type=Agreement.MOU)
        AgreementFactory(status=Agreement.SIGNED, end=end_date, agreement_type=Agreement.SSFA)

        # Mock AgreementValid() to always return True.
        mock_validator = mock.Mock(spec=['is_valid'])
        mock_validator.is_valid = True
        MockAgreementValid.return_value = mock_validator

        # I'm done mocking, it's time to call the function.
        partners.tasks._make_agreement_status_automatic_transitions(self.tenant_countries[0].name)

        expected_call_args = [((agreement, ), {'user': self.admin_user, 'disable_rigid_check': True})
                              for agreement in agreements]
        self._assertCalls(MockAgreementValid, expected_call_args)

        # Verify logged messages.
        expected_call_args = [
            (('Starting agreement auto status transition for country {}'.format(self.tenant_countries[0].name), ), {}),
            (('Total agreements 3', ), {}),
            (('Transitioned agreements 0 ', ), {}),
            ]
        self._assertCalls(mock_logger.info, expected_call_args)

        expected_call_args = [
            (('Bad agreements 0', ), {}),
            (('Bad agreements ids: ', ), {}),
            ]
        self._assertCalls(mock_logger.error, expected_call_args)

    @mock.patch('partners.tasks.AgreementValid')
    def test_make_agreement_status_automatic_transitions_with_mixed_agreements(
            self,
            MockAgreementValid,
            mock_db_connection,
            mock_logger):
        '''Exercise _make_agreement_status_automatic_transitions() when some agreements are valid and some aren't.'''
        end_date = datetime.date.today() + datetime.timedelta(days=2)
        agreements = [AgreementFactory(status=Agreement.SIGNED, end=end_date, agreement_type=Agreement.MOU)
                      for i in range(3)]

        # Create a few items that should be ignored. If they're not ignored, this test will fail.
        AgreementFactory(status=Agreement.SUSPENDED, end=end_date, agreement_type=Agreement.MOU)
        AgreementFactory(status=Agreement.SIGNED,
                         end=datetime.date.today() - datetime.timedelta(days=2),
                         agreement_type=Agreement.MOU)
        AgreementFactory(status=Agreement.SIGNED, end=end_date, agreement_type=Agreement.SSFA)

        def mock_agreement_valid_class_side_effect(*args, **kwargs):
            '''Side effect for my mock AgreementValid() that gets called each time my mock AgreementValid() class
            is instantiated. It gives me the opportunity to modify one of the agreements passed.
            '''
            if args and hasattr(args[0], 'id'):
                if args[0].id == agreements[1].id:
                    # We'll pretend the second agreement made a status transition
                    args[0].status = Agreement.ENDED
                    args[0].save()
            # else:
                # This is a test failure; we always expect (mock) AgreementValid to be called (instantiated) with
                # an agreement passed as the first arg. However the args with which AgreementValid is called are
                # explicitly checked in this test so we don't need to react here.

            return mock.DEFAULT

        # (Mock) AgreementValid() returns a (mock) validator; set up is_valid to return False for the first agreement
        # and True for the other two.
        mock_validator = mock.Mock(spec=['is_valid'], name='mock_validator')
        type(mock_validator).is_valid = mock.PropertyMock(side_effect=[False, True, True])

        MockAgreementValid.side_effect = mock_agreement_valid_class_side_effect
        MockAgreementValid.return_value = mock_validator

        # I'm done mocking, it's time to call the function.
        partners.tasks._make_agreement_status_automatic_transitions(self.tenant_countries[0].name)

        expected_call_args = [((agreement, ), {'user': self.admin_user, 'disable_rigid_check': True})
                              for agreement in agreements]
        self._assertCalls(MockAgreementValid, expected_call_args)

        # Verify logged messages.
        expected_call_args = [
            (('Starting agreement auto status transition for country {}'.format(self.tenant_countries[0].name), ), {}),
            (('Total agreements 3', ), {}),
            (('Transitioned agreements 1 ', ), {}),
            ]
        self._assertCalls(mock_logger.info, expected_call_args)

        expected_call_args = [
            (('Bad agreements 1', ), {}),
            (('Bad agreements ids: {}'.format(agreements[0].id), ), {}),
            ]
        self._assertCalls(mock_logger.error, expected_call_args)


@mock.patch('partners.tasks.logger', spec=['info', 'error'])
@mock.patch('partners.tasks.connection', spec=['set_tenant'])
class TestInterventionStatusAutomaticTransitionTask(FastTenantTestCase):
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

    @mock.patch('partners.tasks._make_intervention_status_automatic_transitions')
    @mock.patch('partners.tasks.Country', spec='objects')
    def test_task(self, MockCountry, mock_make_intervention_status_automatic_transitions, mock_db_connection,
                  mock_logger):
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
        partners.tasks.intervention_status_automatic_transition()

        self._assertCalls(MockCountry.objects.exclude, [((), {'name': 'Global'})])

        # These should have been called once for each tenant country
        self._assertCalls(mock_db_connection.set_tenant, [((country, ), {}) for country in self.tenant_countries])

        self._assertCalls(mock_make_intervention_status_automatic_transitions,
                          [((country.name, ), {}) for country in self.tenant_countries])
