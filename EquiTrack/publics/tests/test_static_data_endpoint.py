from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import AirlineCompanyFactory, DSARegionFactory, CountryFactory, BusinessAreaFactory, \
    WBSFactory, GrantFactory, FundFactory, ExpenseTypeFactory
from t2f.tests.factories import CurrencyFactory


class StaticDataEndpoint(APITenantTestCase):
    def setUp(self):
        super(StaticDataEndpoint, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_urls(self):
        static_data_url = reverse('public_static')
        self.assertEqual(static_data_url, '/api/static_data/')

    def test_endpoint(self):
        # This line is duplicated on purpose. Currency will have always 1+N number of queries
        # because of the exchange rate
        CurrencyFactory()
        CurrencyFactory()
        CurrencyFactory()
        CurrencyFactory()

        # Create one of each model to check if all serializers are working fine
        AirlineCompanyFactory()
        DSARegionFactory()
        CountryFactory()
        BusinessAreaFactory()
        WBSFactory()
        GrantFactory()
        FundFactory()
        ExpenseTypeFactory()

        with self.assertNumQueries(14):
            response = self.forced_auth_req('get', reverse('public_static'),
                                            user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertKeysIn(['dsa_regions',
                           'currencies',
                           'wbs',
                           'travel_types',
                           'countries',
                           'funds',
                           'airlines',
                           'travel_modes',
                           'grants',
                           'expense_types',
                           'business_areas'],
                          response_json,
                          exact=True)
