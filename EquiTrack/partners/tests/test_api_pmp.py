from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
from operator import itemgetter
from unittest import TestCase

from django.core.urlresolvers import reverse
from django.utils.six.moves import range
from rest_framework import status
from tenant_schemas.test.client import TenantClient

from EquiTrack.factories import (
    CurrencyFactory,
    GatewayTypeFactory,
    PartnerFactory,
    UserFactory,
    )
from partners.models import (
    Agreement,
    AgreementAmendment,
    Assessment,
    Intervention,
    InterventionAmendment,
    PartnerOrganization,
    PartnerType,
    )
from EquiTrack.tests.mixins import APITenantTestCase, URLAssertionMixin


class URLsTestCase(URLAssertionMixin, TestCase):
    '''Simple test case to verify URL reversal'''
    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
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


class TestPMPStaticDropdownsListApiView(APITenantTestCase):
    '''exercise PmpStaticDropdownsListApiView'''
    def setUp(self):
        self.user = UserFactory(is_staff=True)
        self.url = reverse("partners_api:dropdown-static-list")
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
                                     ))

    def _assertResponseFundamentals(self, response):
        '''Assert common fundamentals about the response and return the response JSON as a dict.'''
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content.decode('utf-8'))
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
        '''Given a list of 2 tuples of (value, name), returns those in a list in the same format in which I expect
        PmpStaticDropdownsListApiView to format its responses.
        '''
        return sorted([{'value': value, 'label': label} for value, label in choices], key=itemgetter('label'))

    def test_cso_types(self):
        '''Verify the cso_types portion of the response'''
        PartnerFactory(cso_type=PartnerOrganization.CSO_TYPES['International'])
        # These should be filtered out of the endpoint response (https://github.com/unicef/etools/issues/510)
        PartnerFactory(cso_type=None)
        PartnerFactory(cso_type='')

        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)
        self.assertEqual(d['cso_types'], [{'value': PartnerOrganization.CSO_TYPES['International'],
                                           'label': PartnerOrganization.CSO_TYPES['International']}])

    def test_partner_types(self):
        '''Verify the partner_types portion of the response'''
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertEqual(sorted(d['partner_types'], key=itemgetter('label')),
                         self._make_value_label_list_from_choices(PartnerType.CHOICES))

    def test_agency_choices(self):
        '''Verify the agency_choices portion of the response'''
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertEqual(sorted(d['agency_choices'], key=itemgetter('label')),
                         self._make_value_label_list_from_choices(PartnerOrganization.AGENCY_CHOICES))

    def test_assessment_types(self):
        '''Verify the assessment_types portion of the response'''
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertEqual(sorted(d['assessment_types'], key=itemgetter('label')),
                         self._make_value_label_list_from_choices(Assessment.ASSESSMENT_TYPES))

    def test_agreement_types(self):
        '''Verify the assessment_types portion of the response'''
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertEqual(sorted(d['agreement_types'], key=itemgetter('label')),
                         self._make_value_label_list_from_choices(Agreement.AGREEMENT_TYPES))

    def test_agreement_status(self):
        '''Verify the agreement_status portion of the response'''
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertEqual(sorted(d['agreement_status'], key=itemgetter('label')),
                         self._make_value_label_list_from_choices(Agreement.STATUS_CHOICES))

    def test_agreement_amendment_types(self):
        '''Verify the agreement_amendment_types portion of the response'''
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertEqual(sorted(d['agreement_amendment_types'], key=itemgetter('label')),
                         self._make_value_label_list_from_choices(AgreementAmendment.AMENDMENT_TYPES))

    def test_intervention_types(self):
        '''Verify the intervention_doc_type portion of the response'''
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertEqual(sorted(d['intervention_doc_type'], key=itemgetter('label')),
                         self._make_value_label_list_from_choices(Intervention.INTERVENTION_TYPES))

    def test_intervention_status(self):
        '''Verify the intervention_status portion of the response'''
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertEqual(sorted(d['intervention_status'], key=itemgetter('label')),
                         self._make_value_label_list_from_choices(Intervention.INTERVENTION_STATUS))

    def test_intervention_amendment_types(self):
        '''Verify the intervention_amendment_types portion of the response'''
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertEqual(sorted(d['intervention_amendment_types'], key=itemgetter('label')),
                         self._make_value_label_list_from_choices(InterventionAmendment.AMENDMENT_TYPES))

    def test_location_types(self):
        '''Verify the location_types portion of the response'''
        gateway_types = [GatewayTypeFactory() for i in range(3)]

        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        # These are formatted differently than most other elements in the response.
        gateway_types = [{name: getattr(gateway_type, name) for name in ('id', 'name', 'admin_level')}
                         for gateway_type in gateway_types]
        gateway_types.sort(key=itemgetter('id'))
        self.assertEqual(d['location_types'], gateway_types)

    def test_currencies(self):
        '''Verify the currencies portion of the response'''
        # Ensure having no currencies doesn't break anything.
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)
        self.assertEqual(d['currencies'], [])

        # Add some currencies
        choices = []
        for code in ('AAA', 'BBB', 'CCC'):
            currency = CurrencyFactory(code=code)
            choices.append((currency.id, code))

        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertEqual(sorted(d['currencies'], key=itemgetter('label')),
                         self._make_value_label_list_from_choices(choices))

    def test_local_currency(self):
        '''Verify the local_currency portion of the response in two parts'''
        # By default the test user has no local currency set. If that changes, this test will break, so I assert
        # that first.
        self.assertIsNone(self.user.profile.country.local_currency)

        # Verify None returned when no local currency set
        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)
        self.assertIsNone(d['local_currency'])

        # Associate a currency with the test user's country and ensure it's returned.
        currency = CurrencyFactory()
        self.user.profile.country.local_currency = currency
        self.user.profile.country.save()

        response = self.forced_auth_req('get', self.url)
        d = self._assertResponseFundamentals(response)

        self.assertEqual(d['local_currency'], currency.id)


class TestPMPDropdownsListApiView(APITenantTestCase):
    def setUp(self):
        super(TestPMPDropdownsListApiView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.url = reverse("partners_api:dropdown-pmp-list")
        self.client = TenantClient(self.tenant)

        self.expected_keys = sorted((
            u'signed_by_unicef_users',
            u'cp_outputs',
            u'country_programmes',
            u'file_types',
            u'donors'
        ))

    def test_get(self):
        self.client.force_login(self.unicef_staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(response.data.keys()), self.expected_keys)
