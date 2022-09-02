import json

from django.urls import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.publics.models import Currency, TravelExpenseType
from etools.applications.publics.tests.factories import (
    PublicsAirlineCompanyFactory,
    PublicsBusinessAreaFactory,
    PublicsCountryFactory,
    PublicsCurrencyFactory,
    PublicsDSARateFactory,
    PublicsDSARegionFactory,
    PublicsTravelExpenseTypeFactory,
    TravelAgentFactory,
)
from etools.applications.users.tests.factories import UserFactory


class StaticDataEndpoints(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True, realms__data=[])

    def test_urls(self):
        static_data_url = reverse('publics:static')
        self.assertEqual(static_data_url, '/api/static_data/')

        currencies_url = reverse('publics:currencies')
        self.assertEqual(currencies_url, '/api/currencies/')

        dsa_regions_url = reverse('publics:dsa_regions')
        self.assertEqual(dsa_regions_url, '/api/dsa_regions/')

        business_areas_url = reverse('publics:business_areas')
        self.assertEqual(business_areas_url, '/api/business_areas/')

        expense_types_url = reverse('publics:expense_types')
        self.assertEqual(expense_types_url, '/api/expense_types/')

        airlines_url = reverse('publics:airlines')
        self.assertEqual(airlines_url, '/api/airlines/')

    def test_endpoint(self):
        # This line is duplicated on purpose. Currency will have always 1+N number of queries
        # because of the exchange rate
        for __ in range(4):
            PublicsCurrencyFactory()

        # Create one of each model to check if all serializers are working fine
        PublicsAirlineCompanyFactory()
        country = PublicsCountryFactory(currency=None)
        PublicsDSARegionFactory(country=country)
        PublicsBusinessAreaFactory()
        PublicsTravelExpenseTypeFactory()

        with self.assertNumQueries(11):
            response = self.forced_auth_req('get', reverse('publics:static'),
                                            user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertKeysIn(['currencies',
                           'travel_types',
                           'countries',
                           'airlines',
                           'travel_modes',
                           'expense_types',
                           'business_areas'],
                          response_json,
                          exact=True)

    def test_expense_type_factory(self):
        user_1_et = PublicsTravelExpenseTypeFactory(
            title='User 1',
            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER
        )
        user_2_et = PublicsTravelExpenseTypeFactory(
            title='User 2',
            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER
        )

        travel_agent_1_et = PublicsTravelExpenseTypeFactory(
            title='TravelAgent',
            vendor_number='travel_agent_001'
        )
        travel_agent_1 = TravelAgentFactory(name='TravelAgent',
                                            code='travel_agent_001',
                                            expense_type=travel_agent_1_et)
        travel_agent_1_ba = travel_agent_1.country.business_area

        travel_agent_2_et = PublicsTravelExpenseTypeFactory(
            title='TravelAgent 2',
            vendor_number='travel_agent_002'
        )
        travel_agent_2 = TravelAgentFactory(name='TravelAgent 2',
                                            code='travel_agent_002',
                                            expense_type=travel_agent_2_et)
        travel_agent_2_ba = travel_agent_2.country.business_area

        self.assertNotEqual(travel_agent_1_ba, travel_agent_2_ba)

        workspace = self.unicef_staff.profile.country
        workspace.business_area_code = travel_agent_1_ba.code
        workspace.save()

        response = self.forced_auth_req('get', reverse('publics:static'),
                                        user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['expense_types']), 3)
        got_expense_type_ids = {et['id'] for et in response_json['expense_types']}
        self.assertEqual(got_expense_type_ids, {user_1_et.id,
                                                user_2_et.id,
                                                travel_agent_1_et.id})

    def test_currencies_view(self):

        self.assertEqual(Currency.objects.count(), 1)
        for __ in range(3):
            PublicsCurrencyFactory()

        with self.assertNumQueries(5):
            response = self.forced_auth_req('get', reverse('publics:currencies'),
                                            user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)

        self.assertEqual(len(response_json), 4)

        expected_keys = ['iso_4217', 'code', 'exchange_to_dollar', 'id', 'name']
        self.assertKeysIn(expected_keys, response_json[0], exact=True)

    def test_dsa_regions_view(self):
        workspace = self.unicef_staff.profile.country
        workspace.business_area_code = '1234'
        workspace.save()

        business_area = PublicsBusinessAreaFactory(code=workspace.business_area_code)
        country = PublicsCountryFactory(business_area=business_area)

        region_1 = PublicsDSARegionFactory(country=country)
        region_2 = PublicsDSARegionFactory(country=country)
        region_3 = PublicsDSARegionFactory(country=country)

        PublicsDSARateFactory(region=region_1)
        PublicsDSARateFactory(region=region_2)
        PublicsDSARateFactory(region=region_3)

        with self.assertNumQueries(4):
            response = self.forced_auth_req('get', reverse('publics:dsa_regions'),
                                            user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)

        self.assertEqual(len(response_json), 3)

        expected_keys = ['unique_name', 'dsa_amount_usd', 'country', 'area_name', 'area_code', 'label',
                         'dsa_amount_60plus_usd', 'long_name', 'effective_from_date', 'dsa_amount_60plus_local', 'id',
                         'unique_id', 'dsa_amount_local']
        self.assertKeysIn(expected_keys, response_json[0], exact=True)

    def test_business_areas_view(self):
        for __ in range(3):
            PublicsBusinessAreaFactory()

        with self.assertNumQueries(1):
            response = self.forced_auth_req('get', reverse('publics:business_areas'),
                                            user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)

        self.assertEqual(len(response_json), 3)

        expected_keys = ['region', 'code', 'id', 'name', 'default_currency']
        self.assertKeysIn(expected_keys, response_json[0], exact=True)

    def test_expense_types_view(self):
        for __ in range(3):
            PublicsTravelExpenseTypeFactory()

        with self.assertNumQueries(1):
            response = self.forced_auth_req('get', reverse('publics:expense_types'),
                                            user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)

        self.assertEqual(len(response_json), 3)

        expected_keys = ['vendor_number', 'unique', 'id', 'name']
        self.assertKeysIn(expected_keys, response_json[0], exact=True)

    def test_airlines_view(self):
        for __ in range(3):
            PublicsAirlineCompanyFactory()

        with self.assertNumQueries(1):
            response = self.forced_auth_req('get', reverse('publics:airlines'),
                                            user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        self.assertEqual(len(response_json), 3)

        expected_keys = ['id', 'name', 'code']
        self.assertKeysIn(expected_keys, response_json[0], exact=True)
