import datetime
import json
import logging

from django.urls import reverse

import pytz
from freezegun import freeze_time
from pytz import UTC

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.publics.tests.factories import (
    PublicsBusinessAreaFactory,
    PublicsCurrencyFactory,
    PublicsDSARateFactory,
    PublicsDSARegionFactory,
)
from etools.applications.t2f.models import make_travel_reference_number, ModeOfTravel, Travel
from etools.applications.t2f.tests.factories import ItineraryItemFactory, TravelFactory
from etools.applications.users.tests.factories import UserFactory

log = logging.getLogger('__name__')


class OverlappingTravelsTest(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        business_area = PublicsBusinessAreaFactory()

        cls.traveler = UserFactory(is_staff=True)
        cls.traveler.profile.vendor_number = 'usrvnd'
        cls.traveler.profile.save()

        workspace = cls.traveler.profile.country
        workspace.business_area_code = business_area.code
        workspace.save()

        cls.unicef_staff = UserFactory(is_staff=True)
        cls.travel = TravelFactory(reference_number=make_travel_reference_number(),
                                   traveler=cls.traveler,
                                   supervisor=cls.unicef_staff,
                                   start_date=datetime.date(2017, 4, 4),
                                   end_date=datetime.date(2017, 4, 14))
        ItineraryItemFactory(travel=cls.travel)
        ItineraryItemFactory(travel=cls.travel)
        cls.travel.submit_for_approval()
        cls.travel.approve()
        cls.travel.save()

    def test_overlapping_trips(self):
        currency = PublicsCurrencyFactory()
        dsa_region = PublicsDSARegionFactory()

        data = {'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-07',
                               'arrival_date': '2017-04-08',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20',
                               'arrival_date': '2017-05-21',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'activities': [],
                'ta_required': True,
                'international_travel': False,
                'mode_of_travel': [ModeOfTravel.BOAT],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'start_date': '2017-04-07',
                'end_date': '2017-05-22',
                'currency': currency.id,
                'purpose': 'Purpose',
                'additional_note': 'Notes'}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        travel_id = response_json['id']

        with freeze_time(datetime.datetime(2017, 4, 14, 16, 00, tzinfo=UTC)):
            response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                            kwargs={'travel_pk': travel_id,
                                                                    'transition_name': Travel.SUBMIT_FOR_APPROVAL}),
                                            data=response_json, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json,
                         {'non_field_errors': ['You have an existing trip with overlapping dates. '
                                               'Please adjust your trip accordingly.']})

    def test_almost_overlapping_trips(self):
        currency = PublicsCurrencyFactory()
        dsa_rate = PublicsDSARateFactory(effective_from_date=datetime.datetime(2017, 4, 10, 16, 00, tzinfo=UTC))
        dsa_region = dsa_rate.region

        data = {'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14',
                               'arrival_date': '2017-04-15',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20',
                               'arrival_date': '2017-05-21',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'activities': [],
                'ta_required': True,
                'international_travel': False,
                'mode_of_travel': [ModeOfTravel.BOAT],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'start_date': '2017-04-14',
                'end_date': '2017-05-22',
                'currency': currency.id,
                'purpose': 'Purpose',
                'additional_note': 'Notes'}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        with freeze_time(datetime.datetime(2017, 4, 14, 16, 00, tzinfo=UTC)):
            response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                            kwargs={'travel_pk': response_json['id'],
                                                                    'transition_name': Travel.SUBMIT_FOR_APPROVAL}),
                                            data=response_json, user=self.traveler)
        # No error should appear, expected 200
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response.status_code, 200, response_json)

    def test_edit_to_overlap(self):
        currency = PublicsCurrencyFactory()
        dsa_region = PublicsDSARegionFactory()

        data = {'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14',
                               'arrival_date': '2017-04-15',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20',
                               'arrival_date': '2017-05-21',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'activities': [],
                'ta_required': True,
                'international_travel': False,
                'mode_of_travel': [ModeOfTravel.BOAT],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'start_date': '2017-04-14',
                'end_date': '2017-05-22',
                'currency': currency.id,
                'purpose': 'Purpose',
                'additional_note': 'Notes'}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        with freeze_time(datetime.datetime(2017, 4, 14, 16, 00, tzinfo=UTC)):
            response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                            kwargs={'travel_pk': response_json['id'],
                                                                    'transition_name': Travel.SUBMIT_FOR_APPROVAL}),
                                            data=response_json, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response.status_code, 200, response_json)

        travel = Travel.objects.get(id=response_json['id'])
        travel.reject()
        travel.save()

        data = response_json
        # Adjust it to overlap
        data['itinerary'] = [
            {
                'origin': 'Berlin',
                'destination': 'Budapest',
                'departure_date': '2017-04-10',
                'arrival_date': '2017-04-15',
                'dsa_region': dsa_region.id,
                'overnight_travel': False,
                'mode_of_travel': ModeOfTravel.RAIL,
                'airlines': []
            },
            {
                'origin': 'Budapest',
                'destination': 'Berlin',
                'departure_date': '2017-05-20',
                'arrival_date': '2017-05-21',
                'dsa_region': dsa_region.id,
                'overnight_travel': False,
                'mode_of_travel': ModeOfTravel.RAIL,
                'airlines': []
            }
        ]

        response = self.forced_auth_req('patch', reverse('t2f:travels:details:state_change',
                                                         kwargs={'travel_pk': response_json['id'],
                                                                 'transition_name': Travel.SUBMIT_FOR_APPROVAL}),
                                        data=response_json, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        assert response.status_code == 400
        self.assertEqual(response_json,
                         {'non_field_errors': ['You have an existing trip with overlapping dates. '
                                               'Please adjust your trip accordingly.']})

    def test_daylight_saving(self):
        budapest_tz = pytz.timezone('Europe/Budapest')
        self.travel.end_date = budapest_tz.localize(
            datetime.datetime(2017, 10, 29, 2, 0),
            is_dst=True
        ).date()
        self.travel.save()

        # Same date as the previous, but it's already after daylight saving
        start_date = budapest_tz.localize(
            datetime.datetime(2017, 10, 29, 2, 0),
            is_dst=False
        ).isoformat()[:10]

        currency = PublicsCurrencyFactory()
        dsa_region = PublicsDSARegionFactory()

        data = {'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14',
                               'arrival_date': '2017-04-15',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20',
                               'arrival_date': '2017-05-21',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'activities': [],
                'ta_required': True,
                'international_travel': False,
                'mode_of_travel': [ModeOfTravel.BOAT],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'start_date': start_date,
                'end_date': '2017-05-22',
                'currency': currency.id,
                'purpose': 'Purpose',
                'additional_note': 'Notes'}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.traveler)
        self.assertEqual(response.status_code, 201)

    def test_start_end_match(self):
        # the new itinerary start date matches the end date of a
        # current itinerary
        currency = PublicsCurrencyFactory()
        dsa_region = PublicsDSARegionFactory()

        data = {'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14',
                               'arrival_date': '2017-04-20',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20',
                               'arrival_date': '2017-05-21',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'activities': [],
                'ta_required': True,
                'international_travel': False,
                'mode_of_travel': [ModeOfTravel.BOAT],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'start_date': '2017-04-14',
                'end_date': '2017-05-22',
                'currency': currency.id,
                'purpose': 'Purpose',
                'additional_note': 'Notes'}

        response = self.forced_auth_req(
            'post',
            reverse('t2f:travels:list:index'),
            data=data,
            user=self.traveler,
        )
        response_json = json.loads(response.rendered_content)

        travel_id = response_json['id']

        response = self.forced_auth_req(
            'post',
            reverse(
                't2f:travels:details:state_change',
                kwargs={
                    'travel_pk': travel_id,
                    'transition_name': Travel.SUBMIT_FOR_APPROVAL,
                }
            ),
            data=response_json,
            user=self.traveler,
        )
        assert response.status_code == 200

    def test_end_start_match(self):
        # the new itinerary end date matches the start date
        # of a current itinerary
        currency = PublicsCurrencyFactory()
        dsa_region = PublicsDSARegionFactory()

        data = {'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-03-14',
                               'arrival_date': '2017-03-20',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-03-25',
                               'arrival_date': '2017-04-04',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'activities': [],
                'ta_required': True,
                'international_travel': False,
                'mode_of_travel': [ModeOfTravel.BOAT],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'start_date': '2017-03-14',
                'end_date': '2017-04-04',
                'currency': currency.id,
                'purpose': 'Purpose',
                'additional_note': 'Notes'}

        response = self.forced_auth_req(
            'post',
            reverse('t2f:travels:list:index'),
            data=data,
            user=self.traveler,
        )
        response_json = json.loads(response.rendered_content)

        travel_id = response_json['id']

        response = self.forced_auth_req(
            'post',
            reverse(
                't2f:travels:details:state_change',
                kwargs={
                    'travel_pk': travel_id,
                    'transition_name': Travel.SUBMIT_FOR_APPROVAL,
                }
            ),
            data=response_json,
            user=self.traveler,
        )
        assert response.status_code == 200
