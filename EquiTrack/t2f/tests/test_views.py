import json

from unittest.case import skip

from EquiTrack.factories import UserFactory, OfficeFactory, SectionFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.models import DSARegion
from t2f.models import TravelPermission
from t2f.tests.factories import AirlineCompanyFactory, CurrencyFactory

from .factories import TravelFactory


class TravelViews(APITenantTestCase):
    maxDiff = None

    def setUp(self):
        super(TravelViews, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(reference_number='REF1',
                                    traveler=self.traveler,
                                    supervisor=self.unicef_staff)

    @skip('To be fixed')
    def test_travel_creation(self):
        dsaregion = DSARegion.objects.first()
        airlines = AirlineCompanyFactory()
        airlines2 = AirlineCompanyFactory()
        office = OfficeFactory()
        section = SectionFactory()
        currency = CurrencyFactory()

        data = {"deductions": [{"date": "2016-11-16",
                                "breakfast": False,
                                "lunch": False,
                                "dinner": False,
                                "accomodation": False,
                                "no_dsa": False},
                               {"date": "2016-11-17",
                                "breakfast": False,
                                "lunch": False,
                                "dinner": False,
                                "accomodation": False,
                                "no_dsa": False,
                                "day_of_the_week": "Thu"},
                               {"date": "2016-11-18",
                                "breakfast": False,
                                "lunch": False,
                                "dinner": False,
                                "accomodation": False,
                                "no_dsa": False,
                                "day_of_the_week": "Fri"},
                               {"date": "2016-11-19",
                                "breakfast": False,
                                "lunch": False,
                                "dinner": False,
                                "accomodation": False,
                                "no_dsa": False,
                                "day_of_the_week": "Sat"},
                               {"date": "2016-11-20",
                                "breakfast": False,
                                "lunch": False,
                                "dinner": False,
                                "accomodation": False,
                                "no_dsa": False}],
                "itinerary": [{"origin": "a",
                               "destination": "a",
                               "dsa_region": dsaregion.id,
                               "overnight_travel": False,
                               "mode_of_travel": "Plane",
                               "airlines": [airlines.id],
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'departure_date': '2016-11-18T09:06:55.821490'}],
                "clearances": {"medical_clearance": "not_applicable",
                               "security_clearance": "not_applicable",
                               "security_course": "not_applicable"},
                "dsa_total": "0.0000",
                "expenses_total": "0.0000",
                "deductions_total": "0.0000",
                "reference_number": "19/10/41",
                "supervisor": self.traveler.id,
                "office": office.id,
                "end_date": None,
                "section": section.id,
                "international_travel": False,
                "traveler": self.traveler.id,
                "start_date": None,
                "ta_required": True,
                "purpose": None,
                "status": "submitted",
                "mode_of_travel": [],
                "estimated_travel_cost": "0.0000",
                "currency": currency.id}

        response = self.forced_auth_req('post', '/api/t2f/travels/', data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {})
        new_travel_id = response_json['id']

        second_traveler = UserFactory()
        data = {'traveler': second_traveler.id}
        response = self.forced_auth_req('post', '/api/t2f/travels/{}/duplicate_travel/'.format(new_travel_id),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertNotEqual(response_json['id'], new_travel_id)
        self.assertEqual(response_json, {})

    @skip('To be fixed')
    def test_payload(self):
        TravelPermission.objects.create(name='afds', code='can_see_travel_status', user_type='God', status='planned')

        travel = TravelFactory()
        response = self.forced_auth_req('get', '/api/t2f/travels/{}/'.format(travel.id), user=self.unicef_staff)
        self.assertEqual(json.loads(response.rendered_content), {})

