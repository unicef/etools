from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse
from django.db import connection

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.models import TravelExpenseType
from publics.tests.factories import AirlineCompanyFactory, DSARegionFactory, CountryFactory, BusinessAreaFactory, \
    WBSFactory, GrantFactory, FundFactory, ExpenseTypeFactory, TravelAgentFactory
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

        with self.assertNumQueries(16):
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

    def test_expense_type_factory(self):
        user_1_et = ExpenseTypeFactory(title='User 1',
                                       vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER)
        user_2_et = ExpenseTypeFactory(title='User 2',
                                       vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER)

        travel_agent_1_et = ExpenseTypeFactory(title='TravelAgent',
                                               vendor_number='travel_agent_001')
        travel_agent_1 = TravelAgentFactory(name='TravelAgent',
                                            code='travel_agent_001',
                                            expense_type=travel_agent_1_et)
        travel_agent_1_ba = travel_agent_1.country.business_area

        travel_agent_2_et = ExpenseTypeFactory(title='TravelAgent 2',
                                               vendor_number='travel_agent_002')
        travel_agent_2 = TravelAgentFactory(name='TravelAgent 2',
                                            code='travel_agent_002',
                                            expense_type=travel_agent_2_et)
        travel_agent_2_ba = travel_agent_2.country.business_area

        self.assertNotEqual(travel_agent_1_ba, travel_agent_2_ba)

        workspace = self.unicef_staff.profile.country
        workspace.business_area_code = travel_agent_1_ba.code
        workspace.save()

        response = self.forced_auth_req('get', reverse('public_static'),
                                        user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['expense_types']), 3)
        got_expense_type_ids = {et['id'] for et in response_json['expense_types']}
        self.assertEqual(got_expense_type_ids, {user_1_et.id,
                                                user_2_et.id,
                                                travel_agent_1_et.id})
