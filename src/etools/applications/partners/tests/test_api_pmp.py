import json
from operator import itemgetter

from django.test import SimpleTestCase
from django.urls import reverse

from django_tenants.test.client import TenantClient
from rest_framework import status
from unicef_djangolib.fields import CURRENCY_LIST
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.mixins import URLAssertionMixin
from etools.applications.partners.models import (
    Agreement,
    AgreementAmendment,
    Assessment,
    Intervention,
    InterventionAmendment,
    PartnerOrganization,
    PartnerType,
)
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.publics.tests.factories import PublicsCurrencyFactory
from etools.applications.users.tests.factories import UserFactory


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    """Simple test case to verify URL reversal"""

    def test_urls(self):
        """Verify URL pattern names generate the URLs we expect them to."""
        names_and_paths = (
            ('dropdown-pmp-list', 'pmp/', {}),
            ('dropdown-static-list', 'static/', {}),
        )
        self.assertReversal(
            names_and_paths,
            'partners_api:',
            '/api/v2/dropdowns/'
        )
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')


class TestPMPStaticDropdownsListApiView(BaseTenantTestCase):
    """exercise PmpStaticDropdownsListApiView"""
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)
        cls.url = reverse("partners_api:dropdown-static-list")

    def setUp(self):
        self.expected_keys = sorted(('cso_types',
                                     'partner_types',
                                     'agency_choices',
                                     'assessment_types',
                                     'agreement_types',
                                     'agreement_status',
                                     'agreement_amendment_types',
                                     'intervention_doc_type',
                                     'intervention_status',
                                     'intervention_amendment_types',
                                     'currencies',
                                     'local_currency',
                                     'location_types',
                                     'attachment_types',
                                     'attachment_types_active',
                                     'partner_file_types',
                                     'partner_risk_rating',
                                     'sea_risk_ratings',
                                     'gender_equity_sustainability_ratings',
                                     'risk_types',
                                     'cash_transfer_modalities',
                                     ))

    def _assertResponseFundamentals(self, response):
        """Assert common fundamentals about the response and return the response JSON as a dict."""
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, dict)
        self.assertEqual(sorted(response_json.keys()), self.expected_keys)
        for key, value in response_json.items():
            if key != 'local_currency':
                self.assertIsInstance(value, list)
            # else:
                # local_currency's type varies; see test_local_currency()

        return response_json

    @staticmethod
    def _make_value_label_list_from_choices(choices):
        """Given a list of 2 tuples of (value, name), returns those in a list in the same format in which I expect
        PmpStaticDropdownsListApiView to format its responses.
        """
        return sorted(
            [
                {'value': value, 'label': label}
                for value, label in choices
            ],
            key=itemgetter('value')
        )

    def test_cso_types(self):
        """Verify the cso_types portion of the response"""
        PartnerFactory(cso_type=PartnerOrganization.CSO_TYPES['International'])
        # These should be filtered out of the endpoint response (https://github.com/unicef/etools/issues/510)
        PartnerFactory(cso_type='')

        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)
        self.assertCountEqual(
            d['cso_types'],
            [{'value': PartnerOrganization.CSO_TYPES['International'],
              'label': PartnerOrganization.CSO_TYPES['International']}])

    def test_partner_types(self):
        """Verify the partner_types portion of the response"""
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertCountEqual(d['partner_types'],
                              self._make_value_label_list_from_choices(PartnerType.CHOICES))

    def test_agency_choices(self):
        """Verify the agency_choices portion of the response"""
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)
        self.assertCountEqual(
            d['agency_choices'],
            self._make_value_label_list_from_choices(PartnerOrganization.AGENCY_CHOICES))

    def test_assessment_types(self):
        """Verify the assessment_types portion of the response"""
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertCountEqual(d['assessment_types'],
                              self._make_value_label_list_from_choices(Assessment.ASSESSMENT_TYPES))

    def test_agreement_types(self):
        """Verify the assessment_types portion of the response"""
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertCountEqual(d['agreement_types'],
                              self._make_value_label_list_from_choices(Agreement.AGREEMENT_TYPES))

    def test_agreement_status(self):
        """Verify the agreement_status portion of the response"""
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertCountEqual(d['agreement_status'],
                              self._make_value_label_list_from_choices(Agreement.STATUS_CHOICES))

    def test_agreement_amendment_types(self):
        """Verify the agreement_amendment_types portion of the response"""
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertCountEqual(d['agreement_amendment_types'],
                              self._make_value_label_list_from_choices(AgreementAmendment.AMENDMENT_TYPES))

    def test_intervention_types(self):
        """Verify the intervention_doc_type portion of the response"""
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertCountEqual(d['intervention_doc_type'],
                              self._make_value_label_list_from_choices(Intervention.INTERVENTION_TYPES))

    def test_intervention_status(self):
        """Verify the intervention_status portion of the response"""
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertCountEqual(d['intervention_status'],
                              self._make_value_label_list_from_choices(Intervention.INTERVENTION_STATUS))

    def test_intervention_amendment_types(self):
        """Verify the intervention_amendment_types portion of the response"""
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertCountEqual(d['intervention_amendment_types'],
                              self._make_value_label_list_from_choices(InterventionAmendment.AMENDMENT_TYPES))

    def test_location_types(self):
        """Verify the location_types portion of the response"""
        gateway_types = [LocationFactory() for i in range(3)]

        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        # These are formatted differently than most other elements in the response.
        gateway_types = [{name: getattr(gateway_type, name) for name in ('admin_level', 'admin_level_name')}
                         for gateway_type in gateway_types]
        gateway_types.sort(key=lambda gateway_type: gateway_type['admin_level'])
        self.assertCountEqual(d['location_types'], gateway_types)

    def test_currencies(self):
        """Verify the currencies portion of the response"""
        # Add some currencies
        choices = []
        for code in CURRENCY_LIST:
            choices.append((code, code))

        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertCountEqual(d['currencies'],
                              self._make_value_label_list_from_choices(choices))

    def test_local_currency(self):
        """Verify the local_currency portion of the response in two parts"""
        # By default the test user has no local currency set. If that changes, this test will break, so I assert
        # that first.
        self.assertIsNone(self.user.profile.country.local_currency)

        # Verify None returned when no local currency set
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)
        self.assertIsNone(d['local_currency'])

        # Associate a currency with the test user's country and ensure it's returned.
        currency = PublicsCurrencyFactory()
        self.user.profile.country.local_currency = currency
        self.user.profile.country.save()

        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertEqual(d['local_currency'], currency.id)


class TestPMPDropdownsListApiView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.url = reverse("partners_api:dropdown-pmp-list")
        cls.client = TenantClient(cls.tenant)

    def setUp(self):
        super().setUp()
        self.expected_keys = sorted((
            'signed_by_unicef_users',
            'cp_outputs',
            'country_programmes',
            'file_types',
            'donors',
            'grants',
        ))

    def test_get(self):
        self.client.force_login(self.unicef_staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertCountEqual(list(response.data.keys()), self.expected_keys)
