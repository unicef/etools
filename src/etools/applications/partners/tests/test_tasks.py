# Python imports

import datetime
import json
from collections import namedtuple
from datetime import timedelta
from decimal import Decimal
from pprint import pformat
from unittest import mock
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.utils import timezone

from unicef_attachments.models import Attachment
from unicef_locations.tests.factories import LocationFactory

import etools.applications.partners.tasks
from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.organizations.models import OrganizationType
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import Agreement, Intervention, PartnerOrganization
from etools.applications.partners.serializers.exports.vision.interventions_v1 import InterventionSerializer
from etools.applications.partners.synchronizers import PDVisionUploader
from etools.applications.partners.tasks import transfer_active_pds_to_new_cp
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    CoreValuesAssessmentFactory,
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerFactory,
)
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import (
    CountryProgrammeFactory,
    InterventionActivityFactory,
    LowerResultFactory,
    OfficeFactory,
    ReportingRequirementFactory,
    SectionFactory,
)
from etools.applications.users.tasks import sync_realms_to_prp
from etools.applications.users.tests.factories import CountryFactory, GroupFactory, RealmFactory, UserFactory
from etools.applications.vision.models import VisionSyncLog


def _build_country(name):
    """Given a name (e.g. 'test1'), creates a Country object via FactoryBoy. The object is not saved to the database.
    It exists only in memory. We must be careful not to save this because creating a new Country in the database
    complicates schemas.
    """
    country = CountryFactory.build(name='Country {}'.format(name.title()), schema_name=name)
    # Mock save() to prevent inadvertent database changes.
    country.save = mock.Mock()

    return country


def _make_decimal(n):
    """Return a Decimal based on the param n with a trailing .00"""
    return Decimal('{}.00'.format(n))


def _make_past_datetime(n_days):
    """Return a datetime.datetime() that refers to n_days in the past"""
    return timezone.now() - datetime.timedelta(days=n_days)


class TestGetInterventionContext(BaseTenantTestCase):
    """Exercise the tasks' helper function get_intervention_context()"""

    def setUp(self):
        super().setUp()
        self.intervention = InterventionFactory(start=None, end=None)
        self.focal_point_user = UserFactory()

    def test_simple_intervention(self):
        """Exercise get_intervention_context() with a very simple intervention"""
        result = etools.applications.partners.tasks.get_intervention_context(self.intervention)

        self.assertIsInstance(result, dict)
        self.assertEqual(sorted(result.keys()),
                         sorted(['number', 'partner', 'start_date', 'url', 'unicef_focal_points']))
        self.assertEqual(result['number'], str(self.intervention))
        self.assertEqual(result['partner'], self.intervention.agreement.partner.name)
        self.assertEqual(result['start_date'], 'None')
        self.assertEqual(result['url'],
                         '{}/pmp/interventions/{}/details'.format(settings.HOST, self.intervention.id))
        self.assertEqual(result['unicef_focal_points'], [])

    def test_non_trivial_intervention(self):
        """Exercise get_intervention_context() with an intervention that has some interesting detail"""
        self.focal_point_user = get_user_model().objects.first()
        self.intervention.unicef_focal_points.add(self.focal_point_user)

        self.intervention.start = datetime.date(2017, 8, 1)
        self.intervention.save()

        result = etools.applications.partners.tasks.get_intervention_context(self.intervention)

        self.assertIsInstance(result, dict)
        self.assertEqual(sorted(result.keys()),
                         sorted(['number', 'partner', 'start_date', 'url', 'unicef_focal_points']))
        self.assertEqual(result['number'], str(self.intervention))
        self.assertEqual(result['partner'], self.intervention.agreement.partner.name)
        self.assertEqual(result['start_date'], '2017-08-01')
        self.assertEqual(result['url'],
                         '{}/pmp/interventions/{}/details'.format(settings.HOST, self.intervention.id))
        self.assertEqual(result['unicef_focal_points'], [self.focal_point_user.email])


class PartnersTestBaseClass(BaseTenantTestCase):
    """Common elements for most of the tests in this file."""

    def _assertCalls(self, mocked_function, all_expected_call_args):
        """Given a mocked function (like mock_logger.info or mock_connection.set_tentant), asserts that the mock was
        called once for each set of call args, and with the args specified.
        all_expected_call_args should be a list of 2-tuples representing mock call_args. Each 2-tuple looks like --
            ((args), {kwargs})
        https://docs.python.org/3/library/unittest.mock.html#unittest.mock.Mock.call_args
        """
        self.assertEqual(mocked_function.call_count, len(all_expected_call_args))
        i = 0
        for actual_call_args, expected_call_args in zip(mocked_function.call_args_list, all_expected_call_args):
            if actual_call_args != expected_call_args:
                # Provide a more useful error message than Django would.
                s = """In call #%d, call args not as expected.
Expected:
%s

Actual:
%s
                """ % (i, pformat(expected_call_args, indent=4), pformat(tuple(actual_call_args), indent=4))
                self.fail(s)
            self.assertEqual(actual_call_args, expected_call_args)
            i += 1

    def _configure_mock_country(self, MockCountry):
        """helper to perform common configuration of the MockCountry that every task test uses."""
        # We have to mock the Country model because we can't save instances to the database without creating
        # new schemas, so instead we mock the call we expect the task to make and return the value we want the
        # task to get.
        MockCountry.objects = mock.Mock(spec=['exclude'])
        MockCountry.objects.exclude = mock.Mock()
        mock_country_objects_exclude_queryset = mock.Mock(spec=['all'])
        MockCountry.objects.exclude.return_value = mock_country_objects_exclude_queryset
        mock_country_objects_exclude_queryset.all = mock.Mock(return_value=self.tenant_countries)

    @classmethod
    def setUpTestData(cls):
        try:
            cls.admin_user = get_user_model().objects.get(username=settings.TASK_ADMIN_USER)
        except get_user_model().DoesNotExist:
            cls.admin_user = UserFactory(username=settings.TASK_ADMIN_USER)

        # The global "country" should be excluded from processing. Create it to ensure it's ignored during this test.
        cls.global_country = _build_country('Global')
        cls.tenant_countries = [_build_country('test{}'.format(i)) for i in range(3)]

        cls.country_name = cls.tenant_countries[0].name


@mock.patch('etools.applications.partners.tasks.logger', spec=['info', 'error'])
@mock.patch('etools.applications.partners.tasks.connection', spec=['set_tenant'])
class TestAgreementStatusAutomaticTransitionTask(PartnersTestBaseClass):
    """Exercises the agreement_status_automatic_transition() task, including the task itself and its core function
    _make_agreement_status_automatic_transitions().
    """
    @mock.patch('etools.applications.partners.tasks._make_agreement_status_automatic_transitions')
    @mock.patch('etools.applications.partners.tasks.Country', spec='objects')
    def test_task(self, MockCountry, mock_make_agreement_status_automatic_transitions, mock_db_connection, mock_logger):
        """Verify that the task executes once for each tenant country"""
        self._configure_mock_country(MockCountry)

        # I'm done mocking, it's time to call the task.
        etools.applications.partners.tasks.agreement_status_automatic_transition()

        self._assertCalls(MockCountry.objects.exclude, [((), {'name': 'Global'})])

        # These should have been called once for each tenant country
        self._assertCalls(mock_db_connection.set_tenant, [((country, ), {}) for country in self.tenant_countries])

        self._assertCalls(mock_make_agreement_status_automatic_transitions,
                          [((country.name, ), {}) for country in self.tenant_countries])

    def test_make_agreement_status_automatic_transitions_no_agreements(self, mock_db_connection, mock_logger):
        """Exercise _make_agreement_status_automatic_transitions() for the simple case when there's no agreements."""
        # Don't need to mock anything extra, just call the function.
        etools.applications.partners.tasks._make_agreement_status_automatic_transitions(self.country_name)

        # Verify logged messages.
        expected_call_args = [
            (('Starting agreement auto status transition for country {}'.format(self.country_name), ), {}),
            (('Total agreements 0', ), {}),
            (('Transitioned agreements 0 ', ), {}),
        ]
        self._assertCalls(mock_logger.info, expected_call_args)

        expected_call_args = [
            (('Bad agreements 0', ), {}),
            (('Bad agreements ids: ', ), {}),
        ]
        self._assertCalls(mock_logger.error, expected_call_args)

    @mock.patch('etools.applications.partners.tasks.AgreementValid')
    def test_make_agreement_status_automatic_transitions_with_valid_agreements(
            self,
            MockAgreementValid,
            mock_db_connection,
            mock_logger):
        """Exercise _make_agreement_status_automatic_transitions() when all agreements are valid."""
        end_date = datetime.date.today() - datetime.timedelta(days=2)
        # Agreements sort by oldest last, so I make sure my list here is ordered in the same way as they'll be
        # pulled out of the database.
        agreements = [AgreementFactory(status=Agreement.SIGNED, end=end_date, created=_make_past_datetime(i),
                                       agreement_type=Agreement.MOU)
                      for i in range(3)]

        # Create a few items that should be ignored. If they're not ignored, this test will fail.
        # Ignored because of status.
        AgreementFactory(status=Agreement.SUSPENDED, end=end_date, agreement_type=Agreement.MOU)
        # Ignored because of end date.
        AgreementFactory(status=Agreement.SIGNED,
                         end=datetime.date.today() + datetime.timedelta(days=2),
                         agreement_type=Agreement.MOU)
        # Ignored because of type.
        AgreementFactory(status=Agreement.SIGNED, end=end_date, agreement_type=Agreement.SSFA)

        # Mock AgreementValid() so that it always returns True.
        mock_validator = mock.Mock(spec=['is_valid'])
        mock_validator.is_valid = True
        MockAgreementValid.return_value = mock_validator

        # I'm done mocking, it's time to call the function.
        etools.applications.partners.tasks._make_agreement_status_automatic_transitions(self.country_name)

        expected_call_args = [((agreement, ), {'user': self.admin_user, 'disable_rigid_check': True})
                              for agreement in agreements]
        self._assertCalls(MockAgreementValid, expected_call_args)

        # Verify logged messages.
        expected_call_args = [
            (('Starting agreement auto status transition for country {}'.format(self.country_name), ), {}),
            (('Total agreements 3', ), {}),
            (('Transitioned agreements 0 ', ), {}),
        ]
        self._assertCalls(mock_logger.info, expected_call_args)

        expected_call_args = [
            (('Bad agreements 0', ), {}),
            (('Bad agreements ids: ', ), {}),
        ]
        self._assertCalls(mock_logger.error, expected_call_args)

    @mock.patch('etools.applications.partners.tasks.AgreementValid')
    def test_make_agreement_draft_status_automatic_transitions_with_valid_agreements(
            self,
            MockAgreementValid,
            mock_db_connection,
            mock_logger):
        """Exercise _make_agreement_status_automatic_transitions()
        when all agreements are valid."""
        end_date = datetime.date.today() - datetime.timedelta(days=2)
        # Agreements sort by oldest last, so I make sure my list here
        # is ordered in the same way as they'll be pulled out of the database.
        agreements = [
            AgreementFactory(
                status=Agreement.DRAFT,
                end=end_date,
                created=_make_past_datetime(i),
                agreement_type=Agreement.MOU,
            )
            for i in range(3)
        ]

        # Create a few items that should be ignored. If they're not ignored,
        # this test will fail. Ignored because of status.
        AgreementFactory(
            status=Agreement.SUSPENDED,
            end=end_date,
            agreement_type=Agreement.MOU,
        )
        # Ignored because of end date.
        AgreementFactory(
            status=Agreement.DRAFT,
            end=datetime.date.today() + datetime.timedelta(days=2),
            agreement_type=Agreement.MOU,
        )
        # Ignored because of type.
        AgreementFactory(
            status=Agreement.DRAFT,
            end=end_date,
            agreement_type=Agreement.SSFA,
        )

        # Mock AgreementValid() so that it always returns True.
        mock_validator = mock.Mock(spec=['is_valid'])
        mock_validator.is_valid = True
        MockAgreementValid.return_value = mock_validator

        # I'm done mocking, it's time to call the function.
        etools.applications.partners.tasks._make_agreement_status_automatic_transitions(
            self.country_name
        )

        expected_call_args = [
            (
                (agreement, ),
                {
                    'user': self.admin_user,
                    'disable_rigid_check': True
                })
            for agreement in agreements
        ]
        self._assertCalls(MockAgreementValid, expected_call_args)

        # Verify logged messages.
        expected_call_args = [
            (('Starting agreement auto status transition for country {}'.format(
                self.country_name
            ), ), {}),
            (('Total agreements 3', ), {}),
            (('Transitioned agreements 0 ', ), {}),
        ]
        self._assertCalls(mock_logger.info, expected_call_args)

        expected_call_args = [
            (('Bad agreements 0', ), {}),
            (('Bad agreements ids: ', ), {}),
        ]
        self._assertCalls(mock_logger.error, expected_call_args)

    @mock.patch('etools.applications.partners.tasks.AgreementValid')
    def test_make_agreement_status_automatic_transitions_with_mixed_agreements(
            self,
            MockAgreementValid,
            mock_db_connection,
            mock_logger):
        """Exercise _make_agreement_status_automatic_transitions() when some agreements are valid and some aren't."""
        end_date = datetime.date.today() - datetime.timedelta(days=2)
        # Agreements sort by oldest last, so I make sure my list here is ordered in the same way as they'll be
        # pulled out of the database.
        agreements = [AgreementFactory(status=Agreement.SIGNED, end=end_date, created=_make_past_datetime(i),
                                       agreement_type=Agreement.MOU)
                      for i in range(3)]

        # Create a few items that should be ignored. If they're not ignored, this test will fail.
        # Ignored because of status.
        AgreementFactory(status=Agreement.SUSPENDED, end=end_date, agreement_type=Agreement.MOU)
        # Ignored because of end date.
        AgreementFactory(status=Agreement.SIGNED,
                         end=datetime.date.today() + datetime.timedelta(days=2),
                         agreement_type=Agreement.MOU)
        # Ignored because of type.
        AgreementFactory(status=Agreement.SIGNED, end=end_date, agreement_type=Agreement.SSFA)

        def mock_agreement_valid_class_side_effect(*args, **kwargs):
            """Side effect for my mock AgreementValid() that gets called
            each time my mock AgreementValid() class is instantiated.
            It gives me the opportunity to modify one of the agreements passed.
            """
            if args and hasattr(args[0], 'id'):
                if args[0].id == agreements[1].id:
                    # We'll pretend the second agreement made a status
                    # transition
                    args[0].status = Agreement.ENDED
                    args[0].save()

            return mock.DEFAULT

        # (Mock) AgreementValid() returns a (mock) validator; set up is_valid to return False for the first agreement
        # and True for the other two.
        mock_validator = mock.Mock(spec=['is_valid'], name='mock_validator')
        type(mock_validator).is_valid = mock.PropertyMock(side_effect=[False, True, True])

        MockAgreementValid.side_effect = mock_agreement_valid_class_side_effect
        MockAgreementValid.return_value = mock_validator

        # I'm done mocking, it's time to call the function.
        etools.applications.partners.tasks._make_agreement_status_automatic_transitions(self.country_name)

        expected_call_args = [((agreement, ), {'user': self.admin_user, 'disable_rigid_check': True})
                              for agreement in agreements]
        self._assertCalls(MockAgreementValid, expected_call_args)

        # Verify logged messages.
        expected_call_args = [
            (('Starting agreement auto status transition for country {}'.format(self.country_name), ), {}),
            (('Total agreements 3', ), {}),
            (('Transitioned agreements 1 ', ), {}),
        ]
        self._assertCalls(mock_logger.info, expected_call_args)

        expected_call_args = [
            (('Bad agreements 1', ), {}),
            (('Bad agreements ids: {}'.format(agreements[0].id), ), {}),
        ]
        self._assertCalls(mock_logger.error, expected_call_args)

    @mock.patch('etools.applications.partners.tasks.AgreementValid')
    def test_make_agreement_draft_status_automatic_transitions_with_mixed_agreements(
            self,
            MockAgreementValid,
            mock_db_connection,
            mock_logger):
        """Exercise _make_agreement_status_automatic_transitions()
        when some agreements are valid and some aren't."""
        end_date = datetime.date.today() - datetime.timedelta(days=2)
        # Agreements sort by oldest last, so I make sure my list
        # here is ordered in the same way as they'll be
        # pulled out of the database.
        agreements = [
            AgreementFactory(
                status=Agreement.DRAFT,
                end=end_date,
                created=_make_past_datetime(i),
                agreement_type=Agreement.MOU
            )
            for i in range(3)
        ]

        # Create a few items that should be ignored. If they're
        # not ignored, this test will fail. Ignored because of status.
        AgreementFactory(
            status=Agreement.SUSPENDED,
            end=end_date,
            agreement_type=Agreement.MOU,
        )
        # Ignored because of end date.
        AgreementFactory(
            status=Agreement.DRAFT,
            end=datetime.date.today() + datetime.timedelta(days=2),
            agreement_type=Agreement.MOU,
        )
        # Ignored because of type.
        AgreementFactory(
            status=Agreement.DRAFT,
            end=end_date,
            agreement_type=Agreement.SSFA,
        )

        def mock_agreement_valid_class_side_effect(*args, **kwargs):
            """Side effect for my mock AgreementValid() that gets called
            each time my mock AgreementValid() class is instantiated.
            It gives me the opportunity to modify one of the agreements passed.
            """
            if args and hasattr(args[0], 'id'):
                if args[0].id == agreements[1].id:
                    # We'll pretend the second agreement made a status
                    # transition
                    args[0].status = Agreement.SIGNED
                    args[0].save()

            return mock.DEFAULT

        # (Mock) AgreementValid() returns a (mock) validator;
        # set up is_valid to return False for the first agreement
        # and True for the other two.
        mock_validator = mock.Mock(spec=['is_valid'], name='mock_validator')
        type(mock_validator).is_valid = mock.PropertyMock(
            side_effect=[False, True, True]
        )

        MockAgreementValid.side_effect = mock_agreement_valid_class_side_effect
        MockAgreementValid.return_value = mock_validator

        # I'm done mocking, it's time to call the function.
        etools.applications.partners.tasks._make_agreement_status_automatic_transitions(
            self.country_name
        )
        expected_call_args = [
            ((agreement, ), {
                'user': self.admin_user,
                'disable_rigid_check': True
            })
            for agreement in agreements
        ]
        self._assertCalls(MockAgreementValid, expected_call_args)

        # Verify logged messages.
        expected_call_args = [(
            ('Starting agreement auto status transition for country {}'.format(
                self.country_name
            ), ),
            {}
        ),
            (('Total agreements 3', ), {}),
            (('Transitioned agreements 1 ', ), {}),
        ]
        self._assertCalls(mock_logger.info, expected_call_args)

        expected_call_args = [
            (('Bad agreements 1', ), {}),
            (('Bad agreements ids: {}'.format(agreements[0].id), ), {}),
        ]
        self._assertCalls(mock_logger.error, expected_call_args)


@mock.patch('etools.applications.partners.tasks.logger', spec=['info', 'error'])
@mock.patch('etools.applications.partners.tasks.connection', spec=['set_tenant'])
class TestInterventionStatusAutomaticTransitionTask(PartnersTestBaseClass):
    """Exercises the agreement_status_automatic_transition() task, including the task itself and its core function
    _make_agreement_status_automatic_transitions().
    """
    @mock.patch('etools.applications.partners.tasks._make_intervention_status_automatic_transitions')
    @mock.patch('etools.applications.partners.tasks.Country', spec='objects')
    def test_task(self, MockCountry, mock_make_intervention_status_automatic_transitions, mock_db_connection,
                  mock_logger):
        """Verify that the task executes once for each tenant country"""
        self._configure_mock_country(MockCountry)

        # I'm done mocking, it's time to call the task.
        etools.applications.partners.tasks.intervention_status_automatic_transition()

        self._assertCalls(MockCountry.objects.exclude, [((), {'name': 'Global'})])

        # These should have been called once for each tenant country
        self._assertCalls(mock_db_connection.set_tenant, [((country, ), {}) for country in self.tenant_countries])

        self._assertCalls(mock_make_intervention_status_automatic_transitions,
                          [((country.name, ), {}) for country in self.tenant_countries])

    def test_make_intervention_status_automatic_transitions_no_interventions(self, mock_db_connection, mock_logger):
        """Exercise _make_intervention_status_automatic_transitions() for the simple case when there's no
        interventions."""
        # Don't need to mock anything extra, just call the function.
        etools.applications.partners.tasks._make_intervention_status_automatic_transitions(self.country_name)

        # Verify logged messages.
        expected_call_args = [
            (('Starting intervention auto status transition for country {}'.format(self.country_name), ), {}),
            (('Total interventions 0', ), {}),
            (('Transitioned interventions 0 ', ), {}),
        ]
        self._assertCalls(mock_logger.info, expected_call_args)

        expected_call_args = [
            (('Bad interventions 0', ), {}),
            (('Bad interventions ids: ', ), {}),
        ]
        self._assertCalls(mock_logger.error, expected_call_args)

    @mock.patch('etools.applications.partners.tasks.InterventionValid')
    def test_make_intervention_status_automatic_transitions_with_valid_interventions(
            self,
            MockInterventionValid,
            mock_db_connection,
            mock_logger):
        """Exercise _make_intervention_status_automatic_transitions() when all interventions are valid"""
        # Make some interventions that are active that ended yesterday. (The task looks for such interventions.)
        end_date = datetime.date.today() - datetime.timedelta(days=1)
        # Interventions sort by oldest last, so I make sure my list here is ordered in the same way as they'll be
        # pulled out of the database.
        interventions = [InterventionFactory(status=Intervention.ACTIVE, end=end_date, created=_make_past_datetime(i))
                         for i in range(3)]

        # Make an intervention with some associated funds reservation headers that the task should find.
        intervention = InterventionFactory(status=Intervention.ENDED, end=end_date)
        for i in range(3):
            FundsReservationHeaderFactory(
                intervention=intervention,
                outstanding_amt_local=Decimal(0.00),
                actual_amt_local=_make_decimal(i),
                total_amt_local=_make_decimal(i),
            )
        interventions.append(intervention)

        # Create a few items that should be ignored. If they're not ignored, this test will fail.
        # Ignored because of status
        InterventionFactory(status=Intervention.TERMINATED)
        InterventionFactory(status=Intervention.CLOSED)
        InterventionFactory(status=Intervention.SUSPENDED)
        InterventionFactory(status=Intervention.DRAFT)

        # Mock InterventionValid() to always return True.
        mock_validator = mock.Mock(spec=['is_valid'])
        mock_validator.is_valid = True
        MockInterventionValid.return_value = mock_validator

        # I'm done mocking, it's time to call the function.
        etools.applications.partners.tasks._make_intervention_status_automatic_transitions(self.country_name)

        expected_call_args = [((intervention_, ), {'user': self.admin_user, 'disable_rigid_check': True})
                              for intervention_ in interventions]
        self._assertCalls(MockInterventionValid, expected_call_args)

        # Verify logged messages.
        expected_call_args = [
            (('Starting intervention auto status transition for country {}'.format(self.country_name), ), {}),
            (('Total interventions 4', ), {}),
            (('Transitioned interventions 0 ', ), {})]
        self._assertCalls(mock_logger.info, expected_call_args)

        expected_call_args = [
            (('Bad interventions 0', ), {}),
            (('Bad interventions ids: ', ), {}),
        ]
        self._assertCalls(mock_logger.error, expected_call_args)

    @mock.patch('etools.applications.partners.tasks.InterventionValid')
    def test_make_intervention_status_automatic_transitions_with_mixed_interventions(
            self,
            MockInterventionValid,
            mock_db_connection,
            mock_logger):
        """Exercise _make_intervention_status_automatic_transitions() when only some interventions are valid, but
        not all of them.
        """
        # Make some interventions that are active that ended yesterday. (The task looks for such interventions.)
        end_date = datetime.date.today() - datetime.timedelta(days=1)
        # Interventions sort by oldest last, so I make sure my list here is ordered in the same way as they'll be
        # pulled out of the database.
        interventions = [InterventionFactory(status=Intervention.ACTIVE, end=end_date, created=_make_past_datetime(i))
                         for i in range(3)]

        # Make an intervention with some associated funds reservation headers that the task should find.
        intervention = InterventionFactory(status=Intervention.ENDED)
        for i in range(3):
            FundsReservationHeaderFactory(
                intervention=intervention,
                outstanding_amt_local=Decimal(0.00),
                actual_amt_local=_make_decimal(i),
                total_amt_local=_make_decimal(i))
        interventions.append(intervention)

        # Create a few items that should be ignored. If they're not ignored, this test will fail.
        # Ignored because of status
        InterventionFactory(status=Intervention.TERMINATED)
        InterventionFactory(status=Intervention.CLOSED)
        InterventionFactory(status=Intervention.SUSPENDED)
        InterventionFactory(status=Intervention.DRAFT)

        def mock_intervention_valid_class_side_effect(*args, **kwargs):
            """Side effect for my mock InterventionValid() that gets called each time my mock InterventionValid() class
            is instantiated. It gives me the opportunity to modify one of the agreements passed.
            """
            if args and hasattr(args[0], 'id'):
                if args[0].id == interventions[1].id:
                    # We'll pretend the second intervention made a status transition
                    args[0].status = Intervention.CLOSED
                    args[0].save()
            # else:
                # This is a test failure; we always expect (mock) InterventionValid to be called (instantiated) with
                # an agreement passed as the first arg. However the args with which InterventionValid is called are
                # explicitly checked in this test so we don't need to react here.

            return mock.DEFAULT

        # (Mock) InterventionValid() returns a (mock) validator; set up is_valid to return False for the first
        # intervention and True for the others.
        mock_validator = mock.Mock(spec=['is_valid'], name='mock_validator')
        type(mock_validator).is_valid = mock.PropertyMock(side_effect=[False, True, True, True])

        MockInterventionValid.side_effect = mock_intervention_valid_class_side_effect
        MockInterventionValid.return_value = mock_validator

        # I'm done mocking, it's time to call the function.
        etools.applications.partners.tasks._make_intervention_status_automatic_transitions(self.country_name)

        expected_call_args = [((intervention_, ), {'user': self.admin_user, 'disable_rigid_check': True})
                              for intervention_ in interventions]
        self._assertCalls(MockInterventionValid, expected_call_args)

        # Verify logged messages.
        expected_call_args = [
            (('Starting intervention auto status transition for country {}'.format(self.country_name), ), {}),
            (('Total interventions 4', ), {}),
            (('Transitioned interventions 1 ', ), {})]
        self._assertCalls(mock_logger.info, expected_call_args)

        expected_call_args = [
            (('Bad interventions 1', ), {}),
            (('Bad interventions ids: {}'.format(interventions[0].id), ), {}),
        ]
        self._assertCalls(mock_logger.error, expected_call_args)

    @mock.patch("etools.applications.partners.tasks.send_pd_to_vision.delay")
    def test_activate_intervention_with_task(self, send_to_vision_mock, _mock_db_connection, _mock_logger):
        today = datetime.date.today()
        unicef_staff = UserFactory(is_staff=True)

        partner = PartnerFactory(organization=OrganizationFactory(name='Partner 2'))
        partner_user = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=partner.organization
        )
        active_agreement = AgreementFactory(
            partner=partner,
            status=Agreement.SIGNED,
            signed_by_unicef_date=today - datetime.timedelta(days=2),
            signed_by_partner_date=today - datetime.timedelta(days=2),
            start=today - datetime.timedelta(days=2),
        )

        active_intervention = InterventionFactory(
            agreement=active_agreement,
            title='Active Intervention',
            document_type=Intervention.PD,
            start=today - datetime.timedelta(days=1),
            end=today + datetime.timedelta(days=365),
            status=Intervention.SIGNED,
            budget_owner=unicef_staff,
            date_sent_to_partner=today - datetime.timedelta(days=1),
            signed_by_unicef_date=today - datetime.timedelta(days=1),
            signed_by_partner_date=today - datetime.timedelta(days=1),
            unicef_signatory=unicef_staff,
            partner_authorized_officer_signatory=partner.active_staff_members.all().first(),
            cash_transfer_modalities=[Intervention.CASH_TRANSFER_DIRECT],
        )
        active_intervention.flat_locations.add(LocationFactory())
        active_intervention.partner_focal_points.add(partner_user)
        active_intervention.unicef_focal_points.add(unicef_staff)
        active_intervention.offices.add(OfficeFactory())
        active_intervention.sections.add(SectionFactory())
        ReportingRequirementFactory(intervention=active_intervention)
        AttachmentFactory(
            code='partners_intervention_signed_pd',
            content_object=active_intervention,
        )
        FundsReservationHeaderFactory(intervention=active_intervention)

        result_link = InterventionResultLinkFactory(
            intervention=active_intervention,
            cp_output__result_type__name=ResultType.OUTPUT,
        )
        pd_output = LowerResultFactory(result_link=result_link)
        activity = InterventionActivityFactory(result=pd_output)
        activity.time_frames.add(active_intervention.quarters.first())

        # with self.captureOnCommitCallbacks(execute=True) as callbacks:
        #     etools.applications.partners.tasks._make_intervention_status_automatic_transitions(self.country_name)
        etools.applications.partners.tasks._make_intervention_status_automatic_transitions(self.country_name)
        active_intervention.refresh_from_db()
        self.assertEqual(active_intervention.status, Intervention.ACTIVE)
        # skip calling for now. We may need to bring it back at some point
        # send_to_vision_mock.assert_called()


@mock.patch('etools.applications.partners.tasks.logger', spec=['info'])
@mock.patch('etools.applications.partners.tasks.connection', spec=['set_tenant'])
class TestNotifyOfNoFrsSignedInterventionsTask(PartnersTestBaseClass):
    """Exercises the intervention_notification_signed_no_frs() task, including the task itself and its core function
    _notify_of_signed_interventions_with_no_frs().
    """
    @mock.patch('etools.applications.partners.tasks._notify_of_signed_interventions_with_no_frs')
    @mock.patch('etools.applications.partners.tasks.Country', spec='objects')
    def test_task(self, MockCountry, mock_notify_of_signed_interventions_with_no_frs, mock_db_connection, mock_logger):
        """Verify that the task executes once for each tenant country"""
        self._configure_mock_country(MockCountry)

        # I'm done mocking, it's time to call the task.
        etools.applications.partners.tasks.intervention_notification_signed_no_frs()

        self._assertCalls(MockCountry.objects.exclude, [((), {'name': 'Global'})])

        # These should have been called once for each tenant country
        self._assertCalls(mock_db_connection.set_tenant, [((country, ), {}) for country in self.tenant_countries])

        self._assertCalls(mock_notify_of_signed_interventions_with_no_frs,
                          [((country.name, ), {}) for country in self.tenant_countries])

    def test_notify_of_signed_interventions_no_interventions(self, mock_db_connection, mock_logger):
        """Exercise _notify_of_signed_interventions_with_no_frs() for the simple case when there's no interventions."""
        # Don't need to mock anything extra, just call the function.
        etools.applications.partners.tasks._notify_of_signed_interventions_with_no_frs(self.country_name)

        # Verify logged messages.
        expected_call_args = [
            (('Starting intervention signed but no FRs notifications for country {}'.format(self.country_name), ), {}),
        ]
        self._assertCalls(mock_logger.info, expected_call_args)

    @mock.patch('unicef_notification.models.Notification')
    def test_notify_of_signed_interventions_with_some_interventions(
            self,
            mock_notification_model,
            mock_db_connection,
            mock_logger):
        """Exercise _notify_of_signed_interventions_with_no_frs() when it has some interventions to work on"""
        # Create some interventions to work with. Interventions sort by oldest last, so I make sure my list here is
        # ordered in the same way as they'll be pulled out of the database.
        start_on = datetime.date.today() + datetime.timedelta(days=5)
        interventions = [InterventionFactory(status=Intervention.SIGNED, start=start_on, created=_make_past_datetime(i))
                         for i in range(3)]

        # Create a few items that should be ignored. If they're not ignored, this test will fail.
        # Should be ignored because of status
        InterventionFactory(status=Intervention.DRAFT, start=start_on)
        # Should be ignored because of start_date
        InterventionFactory(status=Intervention.SIGNED, start=datetime.date.today() - datetime.timedelta(days=5))
        # Should be ignored because of frs
        intervention = InterventionFactory(status=Intervention.SIGNED, start=start_on)
        for i in range(3):
            FundsReservationHeaderFactory(intervention=intervention, outstanding_amt=Decimal(i),
                                          actual_amt=_make_decimal(i), total_amt=_make_decimal(i))

        # Mock Notifications.objects.create() to return a Mock. In order to *truly* mimic create(), my
        # mock_notification_objects.create() should return a new (mock) object every time, but this lazy way of
        # returning the same object is good enough and still allows me to count calls to .send_notification().
        mock_notification = mock.Mock(spec=['send_notification', 'save', 'full_clean'])
        mock_notification_model.return_value = mock_notification

        # I'm done mocking, it's time to call the function.
        etools.applications.partners.tasks._notify_of_signed_interventions_with_no_frs(self.country_name)

        # Verify that Notification.objects.create() was called as expected.
        expected_call_args = [((), {
            'method_type': mock_notification_model.TYPE_EMAIL,
            'sender': intervention_,
            'recipients': [],
            'cc': [],
            'from_address': '',
            'template_name': 'partners/partnership/signed/frs',
            'template_data': etools.applications.partners.tasks.get_intervention_context(intervention_),
        }) for intervention_ in interventions]
        self._assertCalls(mock_notification_model, expected_call_args)

        # Verify that each notification object that was created had send_notification() called.
        expected_call_args = [((), {})] * len(interventions)
        self._assertCalls(mock_notification.send_notification, expected_call_args)


@mock.patch('etools.applications.partners.tasks.logger', spec=['info'])
@mock.patch('etools.applications.partners.tasks.connection', spec=['set_tenant'])
class TestNotifyOfMismatchedEndedInterventionsTask(PartnersTestBaseClass):
    """Exercises the intervention_notification_ended_fr_outstanding() task, including the task itself and its core
    function _notify_of_ended_interventions_with_mismatched_frs().
    """
    @mock.patch('etools.applications.partners.tasks._notify_of_ended_interventions_with_mismatched_frs')
    @mock.patch('etools.applications.partners.tasks.Country', spec='objects')
    def test_task(self, MockCountry, mock_notify_of_ended_interventions_with_mismatched_frs, mock_db_connection,
                  mock_logger):
        """Verify that the task executes once for each tenant country"""
        self._configure_mock_country(MockCountry)

        # I'm done mocking, it's time to call the task.
        etools.applications.partners.tasks.intervention_notification_ended_fr_outstanding()

        self._assertCalls(MockCountry.objects.exclude, [((), {'name': 'Global'})])

        # These should have been called once for each tenant country
        self._assertCalls(mock_db_connection.set_tenant, [((country, ), {}) for country in self.tenant_countries])

        self._assertCalls(mock_notify_of_ended_interventions_with_mismatched_frs,
                          [((country.name, ), {}) for country in self.tenant_countries])

    def test_notify_of_ended_interventions_no_interventions(self, mock_db_connection, mock_logger):
        """Exercise _notify_of_ended_interventions_with_mismatched_frs() for the simple case of no interventions."""
        # Don't need to mock anything extra, just call the function.
        etools.applications.partners.tasks._notify_of_ended_interventions_with_mismatched_frs(self.country_name)

        # Verify logged messages.
        template = 'Starting intervention signed but FRs Amount and actual do not match notifications for country {}'
        expected_call_args = [((template.format(self.country_name), ), {})]
        self._assertCalls(mock_logger.info, expected_call_args)

    @mock.patch('unicef_notification.models.Notification')
    def test_notify_of_ended_interventions_with_some_interventions(
            self,
            mock_notification_model,
            mock_db_connection,
            mock_logger):
        """Exercise _notify_of_ended_interventions_with_mismatched_frs() when it has some interventions to work on"""
        # Create some interventions to work with. Interventions sort by oldest last, so I make sure my list here is
        # ordered in the same way as they'll be pulled out of the database.
        interventions = [InterventionFactory(status=Intervention.ENDED, created=_make_past_datetime(i))
                         for i in range(3)]

        # Add mismatched funds values to each intervention.
        for intervention in interventions:
            for i in range(3):
                FundsReservationHeaderFactory(intervention=intervention,
                                              actual_amt_local=_make_decimal(i + 1),
                                              total_amt_local=_make_decimal(i))

        # Create a few items that should be ignored. If they're not ignored, this test will fail.
        # Should be ignored because of status even though FRS values are mismatched
        intervention = InterventionFactory(status=Intervention.DRAFT)
        for i in range(3):
            FundsReservationHeaderFactory(intervention=intervention, actual_amt_local=_make_decimal(i + 1),
                                          total_amt_local=_make_decimal(i))

        # Should be ignored because FRS values are not mismatched
        intervention = InterventionFactory(status=Intervention.ENDED)
        for i in range(3):
            FundsReservationHeaderFactory(intervention=intervention, actual_amt_local=_make_decimal(i),
                                          total_amt_local=_make_decimal(i))

        # Mock Notifications.objects.create() to return a Mock. In order to *truly* mimic create(), my
        # mock_notification_objects.create() should return a new (mock) object every time, but the lazy way or
        # returning the same object is good enough and still allows me to count calls to .send_notification().
        mock_notification = mock.Mock(spec=['send_notification', 'save', 'full_clean'])
        mock_notification_model.return_value = mock_notification

        # I'm done mocking, it's time to call the function.
        etools.applications.partners.tasks._notify_of_ended_interventions_with_mismatched_frs(self.country_name)

        # Verify that Notification.objects.create() was called as expected.
        expected_call_args = [((), {
            'method_type': mock_notification_model.TYPE_EMAIL,
            'sender': intervention_,
            'recipients': [],
            'cc': [],
            'from_address': '',
            'template_name': 'partners/partnership/ended/frs/outstanding',
            'template_data': etools.applications.partners.tasks.get_intervention_context(intervention_),
        }) for intervention_ in interventions]
        self._assertCalls(mock_notification_model, expected_call_args)

        # Verify that each created notification object had send_notification() called.
        expected_call_args = [((), {})] * len(interventions)
        self._assertCalls(mock_notification.send_notification, expected_call_args)


@mock.patch('etools.applications.partners.tasks.logger', spec=['info'])
@mock.patch('etools.applications.partners.tasks.connection', spec=['set_tenant'])
class TestNotifyOfInterventionsEndingSoon(PartnersTestBaseClass):
    """Exercises the intervention_notification_ending() task, including the task itself and its core
    function _notify_interventions_ending_soon().
    """
    @mock.patch('etools.applications.partners.tasks._notify_interventions_ending_soon')
    @mock.patch('etools.applications.partners.tasks.Country', spec='objects')
    def test_task(self, MockCountry, mock_notify_interventions_ending_soon, mock_db_connection, mock_logger):
        """Verify that the task executes once for each tenant country"""
        self._configure_mock_country(MockCountry)

        # I'm done mocking, it's time to call the task.
        etools.applications.partners.tasks.intervention_notification_ending()

        self._assertCalls(MockCountry.objects.exclude, [((), {'name': 'Global'})])

        # These should have been called once for each tenant country
        self._assertCalls(mock_db_connection.set_tenant, [((country, ), {}) for country in self.tenant_countries])

        self._assertCalls(mock_notify_interventions_ending_soon,
                          [((country.name, ), {}) for country in self.tenant_countries])

    def test_notify_interventions_ending_soon_no_interventions(self, mock_db_connection, mock_logger):
        """Exercise _notify_interventions_ending_soon() for the simple case of no interventions."""
        # Don't need to mock anything extra, just call the function.
        etools.applications.partners.tasks._notify_interventions_ending_soon(self.country_name)

        # Verify logged messages.
        template = 'Starting interventions almost ending notifications for country {}'
        expected_call_args = [((template.format(self.country_name), ), {})]
        self._assertCalls(mock_logger.info, expected_call_args)

    @mock.patch('unicef_notification.models.Notification')
    def test_notify_interventions_ending_soon_with_some_interventions(
            self,
            mock_notification_model,
            mock_db_connection,
            mock_logger):
        """Exercise _notify_interventions_ending_soon() when there are interventions for it to work on.

        That task specifically works on interventions that will end in 15 and 30 days.
        """
        today = datetime.date.today()

        # Create some interventions to work with. Interventions sort by oldest last, so I make sure my list here is
        # ordered in the same way as they'll be pulled out of the database.
        interventions = []
        for delta in etools.applications.partners.tasks._INTERVENTION_ENDING_SOON_DELTAS:
            end_on = datetime.date.today() + datetime.timedelta(days=delta)
            interventions += [InterventionFactory(status=Intervention.ACTIVE, end=end_on,
                                                  created=_make_past_datetime(i + delta))
                              for i in range(3)]

        # Create a few items that should be ignored. If they're not ignored, this test will fail.
        # Should be ignored because of status
        InterventionFactory(status=Intervention.DRAFT, end=end_on)
        InterventionFactory(status=Intervention.IMPLEMENTED, end=end_on)
        InterventionFactory(status=Intervention.TERMINATED, end=end_on)
        # All of these should be ignored because of end date
        for delta in range(max(etools.applications.partners.tasks._INTERVENTION_ENDING_SOON_DELTAS) + 5):
            if delta not in etools.applications.partners.tasks._INTERVENTION_ENDING_SOON_DELTAS:
                InterventionFactory(status=Intervention.ACTIVE, end=today + datetime.timedelta(days=delta))

        # Mock Notifications.objects.create() to return a Mock. In order to *truly* mimic create(), my
        # mock_notification_objects.create() should return a new (mock) object every time, but the lazy way or
        # returning the same object is good enough and still allows me to count calls to .send_notification()
        # on this single object.
        mock_notification = mock.Mock(spec=['send_notification', 'full_clean', 'save'])
        mock_notification_model.return_value = mock_notification

        # I'm done mocking, it's time to call the function.
        etools.applications.partners.tasks._notify_interventions_ending_soon(self.country_name)

        # Verify that Notification.objects.create() was called as expected.
        expected_call_args = []
        for intervention in interventions:
            template_data = etools.applications.partners.tasks.get_intervention_context(intervention)
            template_data['days'] = str((intervention.end - today).days)
            expected_call_args.append(((), {
                'method_type': mock_notification_model.TYPE_EMAIL,
                'sender': intervention,
                'recipients': [],
                'cc': [],
                'from_address': '',
                'template_name': 'partners/partnership/ending',
                'template_data': template_data,
            }))
        self._assertCalls(mock_notification_model, expected_call_args)

        # Verify that each created notification object had send_notification() called.
        expected_call_args = [((), {}) for intervention in interventions]
        self._assertCalls(mock_notification.send_notification, expected_call_args)


class TestCopyAttachments(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.code = "partners_partner_assessment"
        cls.file_type_partner = AttachmentFileTypeFactory()
        cls.core_value_assessment = CoreValuesAssessmentFactory(
            assessment="sample.pdf"
        )

    def test_call(self):
        attachment = AttachmentFactory(
            content_object=self.core_value_assessment,
            file_type=self.file_type_partner,
            code=self.code,
            file="random.pdf"
        )
        etools.applications.partners.tasks.copy_attachments()
        attachment_update = Attachment.objects.get(pk=attachment.pk)
        self.assertEqual(
            attachment_update.file.name,
            self.core_value_assessment.assessment.name
        )


class TestCheckPCARequired(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("update_notifications")

    def test_command(self):
        send_path = "etools.applications.partners.utils.send_notification_with_template"
        lead_date = datetime.date.today() + datetime.timedelta(
            days=settings.PCA_REQUIRED_NOTIFICATION_LEAD
        )
        cp = CountryProgrammeFactory(to_date=lead_date)
        agreement = AgreementFactory(country_programme=cp)
        budget_owner = UserFactory()
        InterventionFactory(
            document_type=Intervention.PD,
            end=lead_date + datetime.timedelta(days=10),
            agreement=agreement,
            budget_owner=budget_owner,
        )
        mock_send = mock.Mock()
        with mock.patch(send_path, mock_send):
            etools.applications.partners.tasks.check_pca_required()
        self.assertEqual(mock_send.call_count, 1)
        # Verify budget owner is in recipients
        recipients = mock_send.call_args[1]['recipients']
        self.assertIn(budget_owner.email, recipients)


class TestCheckPCAMissing(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("update_notifications")

    def test_command(self):
        send_path = "etools.applications.partners.utils.send_notification_with_template"
        date_past = datetime.date.today() - datetime.timedelta(days=10)
        date_future = datetime.date.today() + datetime.timedelta(days=10)
        partner = PartnerFactory()
        cp = CountryProgrammeFactory(
            from_date=date_past,
            to_date=datetime.date.today(),
        )
        agreement = AgreementFactory(
            partner=partner,
            agreement_type=Agreement.PCA,
            country_programme=cp,
        )
        budget_owner = UserFactory()
        InterventionFactory(
            document_type=Intervention.PD,
            start=date_past + datetime.timedelta(days=1),
            end=date_future,
            agreement=agreement,
            budget_owner=budget_owner,
        )
        mock_send = mock.Mock()
        with mock.patch(send_path, mock_send):
            etools.applications.partners.tasks.check_pca_missing()
        self.assertEqual(mock_send.call_count, 1)
        # Verify budget owner is in recipients
        recipients = mock_send.call_args[1]['recipients']
        self.assertIn(budget_owner.email, recipients)


class TestCheckInterventionDraftStatus(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("update_notifications")

    def test_task(self):
        send_path = "etools.applications.partners.utils.send_notification_with_template"
        tz = timezone.get_default_timezone()
        budget_owner = UserFactory()
        intervention = InterventionFactory(status=Intervention.DRAFT, budget_owner=budget_owner)
        intervention.created = datetime.datetime(2018, 1, 1, 12, 55, 12, 12345, tzinfo=tz)
        intervention.save()
        mock_send = mock.Mock()
        with mock.patch(send_path, mock_send):
            etools.applications.partners.tasks.check_intervention_draft_status()
        self.assertEqual(mock_send.call_count, 1)
        # Verify budget owner is in recipients
        recipients = mock_send.call_args[1]['recipients']
        self.assertIn(budget_owner.email, recipients)


class TestCheckInterventionPastStartStatus(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("update_notifications")

    def test_task(self):
        send_path = "etools.applications.partners.utils.send_notification_with_template"
        budget_owner = UserFactory()
        intervention = InterventionFactory(
            status=Intervention.SIGNED,
            start=datetime.date.today() - datetime.timedelta(days=2),
            budget_owner=budget_owner,
        )
        FundsReservationHeaderFactory(intervention=intervention)
        mock_send = mock.Mock()
        with mock.patch(send_path, mock_send):
            etools.applications.partners.tasks.check_intervention_past_start()
        self.assertEqual(mock_send.call_count, 1)
        # Verify budget owner is in recipients
        recipients = mock_send.call_args[1]['recipients']
        self.assertIn(budget_owner.email, recipients)


class TestInterventionExpired(BaseTenantTestCase):
    def test_task(self):
        today = timezone.now().date()
        old_cp = CountryProgrammeFactory(
            from_date=today - datetime.timedelta(days=5),
            to_date=today - datetime.timedelta(days=2),
        )
        active_cp = CountryProgrammeFactory(
            from_date=today - datetime.timedelta(days=1),
            to_date=today + datetime.timedelta(days=10),
        )

        today = datetime.date.today()
        intervention_1 = InterventionFactory(
            contingency_pd=True,
            status=Intervention.SIGNED,
            start=today - datetime.timedelta(days=2),
            country_programmes=[old_cp],
        )
        intervention_2 = InterventionFactory(
            contingency_pd=True,
            status=Intervention.SIGNED,
            start=today - datetime.timedelta(days=2),
            country_programmes=[old_cp, active_cp],
        )
        etools.applications.partners.tasks.intervention_expired()
        intervention_1.refresh_from_db()
        intervention_2.refresh_from_db()
        self.assertEqual(intervention_1.status, Intervention.EXPIRED)
        self.assertEqual(intervention_2.status, Intervention.SIGNED)


class ActivePDTransferToNewCPTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.today = timezone.now().date()
        cls.old_cp = CountryProgrammeFactory(
            from_date=cls.today - timedelta(days=5),
            to_date=cls.today - timedelta(days=2),
        )
        cls.partner = PartnerFactory()
        cls.old_agreement = AgreementFactory(partner=cls.partner, country_programme=cls.old_cp)

    def _init_new_cp(self):
        self.active_cp = CountryProgrammeFactory(
            from_date=self.today - timedelta(days=1),
            to_date=self.today + timedelta(days=10),
        )

    def test_transfer_without_active_cp(self):
        pd = InterventionFactory(
            agreement=self.old_agreement,
            status=Intervention.ACTIVE,
            start=self.today - timedelta(days=4),
            end=self.today + timedelta(days=4),
            country_programmes=[self.old_cp],
        )

        transfer_active_pds_to_new_cp()

        pd.refresh_from_db()
        self.assertListEqual(list(pd.country_programmes.all()), [self.old_cp])

    def test_transfer(self):
        pd = InterventionFactory(
            agreement=self.old_agreement,
            status=Intervention.ACTIVE,
            start=self.today - timedelta(days=4),
            end=self.today + timedelta(days=4),
            country_programmes=[self.old_cp],
        )
        self._init_new_cp()

        transfer_active_pds_to_new_cp()

        pd.refresh_from_db()
        self.assertListEqual(list(pd.country_programmes.all().order_by('id')),
                             sorted([self.old_cp, self.active_cp], key=lambda x: x.pk))

    def test_skip_transfer_if_one_programme_already_active(self):
        second_active_cp = CountryProgrammeFactory(
            from_date=self.today - timedelta(days=1),
            to_date=self.today + timedelta(days=10),
        )

        pd = InterventionFactory(
            agreement=self.old_agreement,
            status=Intervention.ACTIVE,
            start=self.today - timedelta(days=4),
            end=self.today + timedelta(days=4),
            country_programmes=[self.old_cp, second_active_cp],
        )
        self._init_new_cp()

        transfer_active_pds_to_new_cp()

        pd.refresh_from_db()
        self.assertListEqual(list(pd.country_programmes.all()), [self.old_cp, second_active_cp])


@mock.patch('etools.applications.partners.tasks.logger', spec=['info', 'warning', 'error', 'exception'])
@override_settings(
    EZHACT_PD_VISION_URL='https://example.com/upload/pd/',
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
)
class SendPDToVisionTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.draft_intervention = InterventionFactory()
        cls.active_intervention = InterventionFactory(status=Intervention.ACTIVE)
        cls.result_link = InterventionResultLinkFactory(
            intervention=cls.active_intervention,
            cp_output__result_type__name=ResultType.OUTPUT,
        )
        cls.pd_output = LowerResultFactory(result_link=cls.result_link, code="0", name="Lower Result 0")
        cls.activity = InterventionActivityFactory(result=cls.pd_output, name="Distribute kits")

    def test_sync_validation_error(self, logger_mock):
        etools.applications.partners.tasks.send_pd_to_vision(connection.tenant.name, self.draft_intervention.pk)
        logger_mock.info.assert_called_with('Instance is not ready to be synchronized')

    @mock.patch(
        'etools.applications.partners.synchronizers.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text', 'json'])(502, '', lambda: None)
    )
    def test_sync_bad_response(self, _requests_mock, logger_mock):
        etools.applications.partners.tasks.send_pd_to_vision(connection.tenant.name, self.active_intervention.pk)
        self.assertTrue(mock.call('Received 502 from vision synchronizer. retrying') in logger_mock.info.mock_calls)
        self.assertTrue(
            mock.call(
                f'Received 502 from vision synchronizer after 3 attempts. '
                f'PD number: {self.active_intervention.pk}. Business area code: {connection.tenant.business_area_code}'
            ) in logger_mock.exception.mock_calls
        )
        vision_log = VisionSyncLog.objects.filter(
            country=connection.tenant,
            handler_name='PDVisionUploader'
        ).last()
        self.assertTrue(vision_log.data, InterventionSerializer(self.active_intervention).data)

    @mock.patch(
        'etools.applications.partners.synchronizers.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text', 'json'])(200, '{}', lambda: {})
    )
    def test_sync_success(self, _requests_mock, logger_mock):
        etools.applications.partners.tasks.send_pd_to_vision(connection.tenant.name, self.active_intervention.pk)
        self.assertTrue(mock.call('Completed pd synchronization') in logger_mock.info.mock_calls)
        vision_log = VisionSyncLog.objects.filter(
            country=connection.tenant,
            handler_name='PDVisionUploader'
        ).last()
        self.assertTrue(vision_log.data, InterventionSerializer(self.active_intervention).data)

    @mock.patch('etools.applications.partners.synchronizers.requests.post',
                return_value=namedtuple('Response', ['status_code', 'text', 'json'])(200, '', lambda: None))
    def test_business_code_in_data(self, requests_mock, _logger_mock):
        etools.applications.partners.tasks.send_pd_to_vision(connection.tenant.name, self.active_intervention.pk)
        self.assertIn('business_area', json.loads(requests_mock.mock_calls[0][2]['data']))

    def test_body_rendering(self, _logger_mock):
        synchronizer = PDVisionUploader(Intervention.objects.detail_qs().get(pk=self.active_intervention.pk))
        str_data = synchronizer.render()
        self.assertIsInstance(str_data, bytes)
        self.assertGreater(len(str_data), 100)

    @mock.patch(
        'etools.applications.partners.synchronizers.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text', 'json'])(200, '{}', lambda: {})
    )
    def test_payload_sent_to_vision_contain_code_prefix(self, requests_mock, _logger_mock):
        etools.applications.partners.tasks.send_pd_to_vision(connection.tenant.name, self.active_intervention.pk)

        sent_body = requests_mock.mock_calls[0][2]['data']
        payload = json.loads(sent_body)

        result_links = payload.get('result_links', [])
        ll_results = result_links[0].get('ll_results', [])
        activities = ll_results[0].get('activities', [])

        matched = {a.get('id'): a for a in activities}.get(self.activity.id)
        self.assertIsNotNone(matched, 'Created activity must be present in payload')
        self.assertTrue(
            matched['name'].startswith(f"{self.activity.code} "),
            f"Activity name should start with code prefix. Got: {matched['name']}"
        )


class TestRealmsPRPExport(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        UserFactory(email='prp@example.com', realms__data=[])

    @override_settings(UNICEF_USER_EMAIL="@another_example.com",
                       PRP_API_ENDPOINT='http://example.com/api/',
                       PRP_API_USER='prp@example.com')
    @patch('etools.applications.users.signals.sync_realms_to_prp.apply_async')
    @patch(
        'etools.applications.partners.prp_api.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text'])(200, '{}')
    )
    def test_realms_sync_on_create(self, requests_post_mock, sync_mock):
        sync_mock.side_effect = lambda *args, **_kwargs: sync_realms_to_prp(*args[0])

        user = UserFactory(realms__data=[])
        self.assertFalse(user.is_unicef_user())
        with self.captureOnCommitCallbacks(execute=True) as commit_callbacks:
            realm = RealmFactory(user=user, group=GroupFactory(name='IP Viewer'))
        sync_mock.assert_called_with(
            (user.pk, realm.modified.timestamp()),
            eta=realm.modified + datetime.timedelta(minutes=5),
        )
        requests_post_mock.assert_called()
        self.assertEqual(len(commit_callbacks), 1)

    @override_settings(UNICEF_USER_EMAIL="@another_example.com",
                       PRP_API_ENDPOINT='http://example.com/api/',
                       PRP_API_USER='prp@example.com')
    @patch('etools.applications.users.signals.sync_realms_to_prp.apply_async')
    @patch(
        'etools.applications.partners.prp_api.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text'])(200, '{}')
    )
    def test_realms_call_once_on_create(self, requests_post_mock, sync_mock):
        sync_mock.side_effect = lambda *args, **_kwargs: sync_realms_to_prp(*args[0])

        user = UserFactory(realms__data=[])
        self.assertFalse(user.is_unicef_user())
        with self.captureOnCommitCallbacks(execute=False) as commit_callbacks:
            RealmFactory(user=user, group=GroupFactory(name='IP Viewer'))
            RealmFactory(user=user, group=GroupFactory(name='IP Editor'))

        for callback in commit_callbacks:
            callback()

        self.assertEqual(sync_mock.call_count, 2)
        requests_post_mock.assert_called_once()

    @override_settings(UNICEF_USER_EMAIL="@another_example.com",
                       PRP_API_ENDPOINT='http://example.com/api/',
                       PRP_API_USER='prp@example.com')
    @patch('etools.applications.users.signals.sync_realms_to_prp.apply_async')
    @patch(
        'etools.applications.partners.prp_api.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text'])(200, '{}')
    )
    def test_realms_sync_on_delete(self, requests_post_mock, sync_mock):
        sync_mock.side_effect = lambda *args, **_kwargs: sync_realms_to_prp(*args[0])

        user = UserFactory(realms__data=['Auditor'])
        self.assertFalse(user.is_unicef_user())
        realm = RealmFactory(user=user, group=GroupFactory(name='IP Editor'))
        with self.captureOnCommitCallbacks(execute=True) as commit_callbacks:
            realm.delete()
        sync_mock.assert_called()
        requests_post_mock.assert_not_called()
        self.assertEqual(len(commit_callbacks), 1)

    @override_settings(UNICEF_USER_EMAIL="@another_example.com",
                       PRP_API_ENDPOINT='http://example.com/api/',
                       PRP_API_USER='prp@example.com')
    @patch('etools.applications.users.signals.sync_realms_to_prp.apply_async')
    @patch(
        'etools.applications.partners.prp_api.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text'])(200, '{}')
    )
    def test_realms_sync_on_change(self, requests_post_mock, sync_mock):
        sync_mock.side_effect = lambda *args, **_kwargs: sync_realms_to_prp(*args[0])

        user = UserFactory(realms__data=[])
        self.assertFalse(user.is_unicef_user())
        realm = RealmFactory(user=user, group=GroupFactory(name='IP Viewer'))
        with self.captureOnCommitCallbacks(execute=True) as commit_callbacks:
            realm.is_active = False
            realm.save()
        sync_mock.assert_called_with(
            (user.pk, realm.modified.timestamp()),
            eta=realm.modified + datetime.timedelta(minutes=5),
        )
        requests_post_mock.assert_called()
        self.assertEqual(len(commit_callbacks), 1)

    @override_settings(UNICEF_USER_EMAIL="@another_example.com",
                       PRP_API_ENDPOINT='http://example.com/api/',
                       PRP_API_USER='prp@example.com')
    @patch('etools.applications.users.signals.sync_realms_to_prp.apply_async')
    @patch(
        'etools.applications.partners.prp_api.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text'])(200, '{}')
    )
    def test_realms_sync_on_non_partner_role(self, requests_post_mock, sync_mock):
        sync_mock.side_effect = lambda *args, **_kwargs: sync_realms_to_prp(*args[0])

        user = UserFactory(realms__data=[])
        self.assertFalse(user.is_unicef_user())
        realm = RealmFactory(user=user, group=GroupFactory(name='Auditor'))
        with self.captureOnCommitCallbacks(execute=True) as commit_callbacks:
            realm.is_active = False
            realm.save()
        sync_mock.assert_called_with(
            (user.pk, realm.modified.timestamp()),
            eta=realm.modified + datetime.timedelta(minutes=5),
        )
        requests_post_mock.assert_not_called()
        self.assertEqual(len(commit_callbacks), 1)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    @patch('etools.applications.users.signals.sync_realms_to_prp.apply_async')
    def test_realms_sync_unicef(self, sync_mock):
        user = UserFactory()
        self.assertTrue(user.is_unicef_user())
        with self.captureOnCommitCallbacks(execute=True) as commit_callbacks:
            RealmFactory(user=user)
        sync_mock.assert_not_called()
        self.assertEqual(len(commit_callbacks), 0)


class TestPartnerAssessmentExpires(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("update_notifications")
        cls.today = timezone.now().date()
        cls.partner_1 = PartnerFactory(
            organization=OrganizationFactory(organization_type=OrganizationType.CIVIL_SOCIETY_ORGANIZATION)
        )
        cls.intervention_1 = InterventionFactory(
            agreement=AgreementFactory(partner=cls.partner_1),
            status=Intervention.ACTIVE,
            start=cls.today - datetime.timedelta(days=2),
        )
        cls.focal_point = UserFactory()
        cls.focal_point.profile.country_override = connection.tenant
        cls.focal_point.profile.save()
        cls.intervention_1.unicef_focal_points.add(cls.focal_point)

    def test_task_last_assessment_date_expiring(self):
        last_assessment_date = self.today - datetime.timedelta(days=PartnerOrganization.EXPIRING_ASSESSMENT_LIMIT_YEAR * 365 - 30)
        self.partner_1.last_assessment_date = last_assessment_date
        self.partner_1.save()

        send_path = "etools.applications.partners.tasks.send_notification_with_template"
        mock_send = mock.Mock()
        with mock.patch(send_path, mock_send):
            etools.applications.partners.tasks.notify_partner_assessment_expires()
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args.kwargs['recipients'], [self.focal_point.email])

    def test_task_core_assessment_date_expiring(self):
        core_values_assessment_date = self.today - datetime.timedelta(days=PartnerOrganization.EXPIRING_ASSESSMENT_LIMIT_YEAR * 365 - 60)

        self.partner_1.core_values_assessment_date = core_values_assessment_date
        self.partner_1.save()

        send_path = "etools.applications.partners.tasks.send_notification_with_template"
        mock_send = mock.Mock()
        with mock.patch(send_path, mock_send):
            etools.applications.partners.tasks.notify_partner_assessment_expires()
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args.kwargs['recipients'], [self.focal_point.email])

    def test_task_focal_point_without_country(self):
        core_values_assessment_date = self.today - datetime.timedelta(days=PartnerOrganization.EXPIRING_ASSESSMENT_LIMIT_YEAR * 365 - 60)

        self.partner_1.core_values_assessment_date = core_values_assessment_date
        self.partner_1.save()

        focal_point = UserFactory(profile__country=None)
        self.intervention_1.unicef_focal_points.remove(self.focal_point)
        self.intervention_1.unicef_focal_points.add(focal_point)
        self.assertIsNone(focal_point.profile.country)

        send_path = "etools.applications.partners.tasks.send_notification_with_template"
        mock_send = mock.Mock()
        with mock.patch(send_path, mock_send):
            etools.applications.partners.tasks.notify_partner_assessment_expires()
        self.assertEqual(mock_send.call_count, 0)

    def test_task_excluded_pd_status(self):
        core_values_assessment_date = self.today - datetime.timedelta(days=PartnerOrganization.EXPIRING_ASSESSMENT_LIMIT_YEAR * 365 - 60)

        self.partner_1.core_values_assessment_date = core_values_assessment_date
        self.partner_1.save()
        self.intervention_1.status = Intervention.CLOSED
        self.intervention_1.save()

        send_path = "etools.applications.partners.tasks.send_notification_with_template"
        mock_send = mock.Mock()
        with mock.patch(send_path, mock_send):
            etools.applications.partners.tasks.notify_partner_assessment_expires()
        self.assertEqual(mock_send.call_count, 0)
