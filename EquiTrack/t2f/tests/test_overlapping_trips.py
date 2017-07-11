from __future__ import unicode_literals

import logging

import json
from datetime import datetime
import pytz
from pytz import UTC
from freezegun import freeze_time

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import BusinessAreaFactory, DSARegionFactory, DSARateFactory, ExpenseTypeFactory
from t2f.models import ModeOfTravel, make_travel_reference_number, Travel
from t2f.tests.factories import CurrencyFactory, IteneraryItemFactory

from .factories import TravelFactory

log = logging.getLogger('__name__')


class OverlappingTravelsTest(APITenantTestCase):
    def setUp(self):
        super(OverlappingTravelsTest, self).setUp()
        business_area = BusinessAreaFactory()

        self.traveler = UserFactory(is_staff=True)
        self.traveler.profile.vendor_number = 'usrvnd'
        self.traveler.profile.save()

        workspace = self.traveler.profile.country
        workspace.business_area_code = business_area.code
        workspace.save()

        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(reference_number=make_travel_reference_number(),
                                    traveler=self.traveler,
                                    supervisor=self.unicef_staff,
                                    start_date=datetime(2017, 4, 4, 12, 00, tzinfo=UTC),
                                    end_date=datetime(2017, 4, 14, 16, 00, tzinfo=UTC))
        self.travel.expenses.all().delete()
        IteneraryItemFactory(travel=self.travel)
        IteneraryItemFactory(travel=self.travel)
        self.travel.submit_for_approval()
        self.travel.approve()
        self.travel.send_for_payment()
        self.travel.save()

    def test_overlapping_trips(self):
        currency = CurrencyFactory()
        dsa_region = DSARegionFactory()

        data = {'deductions': [],
                'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-07T17:06:55.821490',
                               'arrival_date': '2017-04-08T17:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20T12:06:55.821490',
                               'arrival_date': '2017-05-21T12:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'activities': [],
                'cost_assignments': [],
                'clearances': {'medical_clearance': 'requested',
                               'security_clearance': 'requested',
                               'security_course': 'requested'},
                'ta_required': True,
                'international_travel': False,
                'mode_of_travel': [ModeOfTravel.BOAT],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'start_date': '2017-04-07T15:02:13+01:00',
                'end_date': '2017-05-22T15:02:13+01:00',
                'currency': currency.id,
                'purpose': 'Purpose',
                'additional_note': 'Notes'}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        travel_id = response_json['id']

        with freeze_time(datetime(2017, 4, 14, 16, 00, tzinfo=UTC)):
            response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                            kwargs={'travel_pk': travel_id,
                                                                    'transition_name': 'submit_for_approval'}),
                                            data=response_json, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json,
                         {'non_field_errors': ['You have an existing trip with overlapping dates. '
                                               'Please adjust your trip accordingly.']})

    def test_almost_overlapping_trips(self):
        currency = CurrencyFactory()
        expense_type = ExpenseTypeFactory()
        dsa_rate = DSARateFactory(effective_from_date=datetime(2017, 4, 10, 16, 00, tzinfo=UTC))
        dsa_region = dsa_rate.region

        data = {'deductions': [],
                'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14T17:06:55.821490',
                               'arrival_date': '2017-04-15T17:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20T12:06:55.821490',
                               'arrival_date': '2017-05-21T12:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'activities': [],
                'cost_assignments': [],
                'clearances': {'medical_clearance': 'requested',
                               'security_clearance': 'requested',
                               'security_course': 'requested'},
                'ta_required': True,
                'international_travel': False,
                'mode_of_travel': [ModeOfTravel.BOAT],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'start_date': '2017-04-14T16:05:00+00:00',
                'end_date': '2017-05-22T15:02:13+00:00',
                'currency': currency.id,
                'purpose': 'Purpose',
                'additional_note': 'Notes',
                'expenses': [{'amount': '120',
                              'type': expense_type.id,
                              'currency': currency.id,
                              'document_currency': currency.id}]}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        with freeze_time(datetime(2017, 4, 14, 16, 00, tzinfo=UTC)):
            response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                            kwargs={'travel_pk': response_json['id'],
                                                                    'transition_name': 'submit_for_approval'}),
                                            data=response_json, user=self.traveler)
        # No error should appear, expected 200
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response.status_code, 200, response_json)
        response_json = json.loads(response.rendered_content)

        travel = Travel.objects.get(id=response_json['id'])
        travel.approve()
        travel.save()

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': response_json['id'],
                                                                'transition_name': 'send_for_payment'}),
                                        data=response_json, user=self.traveler)
        self.assertEqual(response.status_code, 200)

    def test_edit_to_overlap(self):
        currency = CurrencyFactory()
        dsa_region = DSARegionFactory()

        data = {'deductions': [],
                'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14T17:06:55.821490',
                               'arrival_date': '2017-04-15T17:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20T12:06:55.821490',
                               'arrival_date': '2017-05-21T12:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'activities': [],
                'cost_assignments': [],
                'clearances': {'medical_clearance': 'requested',
                               'security_clearance': 'requested',
                               'security_course': 'requested'},
                'ta_required': True,
                'international_travel': False,
                'mode_of_travel': [ModeOfTravel.BOAT],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'start_date': '2017-04-14T16:05:00+00:00',
                'end_date': '2017-05-22T15:02:13+00:00',
                'currency': currency.id,
                'purpose': 'Purpose',
                'additional_note': 'Notes'}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)

        with freeze_time(datetime(2017, 4, 14, 16, 00, tzinfo=UTC)):
            response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                            kwargs={'travel_pk': response_json['id'],
                                                                    'transition_name': 'submit_for_approval'}),
                                            data=response_json, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response.status_code, 200, response_json)

        travel = Travel.objects.get(id=response_json['id'])
        travel.reject()
        travel.save()

        data = response_json
        # Adjust it to overlap
        data['itinerary'] = [
          {'origin': 'Berlin',
           'destination': 'Budapest',
           'departure_date': '2017-04-10T16:05:00+00:00',
           'arrival_date': '2017-04-15T17:06:55.821490',
           'dsa_region': dsa_region.id,
           'overnight_travel': False,
           'mode_of_travel': ModeOfTravel.RAIL,
           'airlines': []},
          {'origin': 'Budapest',
           'destination': 'Berlin',
           'departure_date': '2017-05-20T12:06:55.821490',
           'arrival_date': '2017-05-21T12:06:55.821490',
           'dsa_region': dsa_region.id,
           'overnight_travel': False,
           'mode_of_travel': ModeOfTravel.RAIL,
           'airlines': []}
        ]

        response = self.forced_auth_req('patch', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': response_json['id'],
                                                                'transition_name': 'submit_for_approval'}),
                                        data=response_json, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json,
                         {'non_field_errors': ['You have an existing trip with overlapping dates. '
                                               'Please adjust your trip accordingly.']})

    def test_daylight_saving(self):
        budapest_tz = pytz.timezone('Europe/Budapest')
        self.travel.end_date = budapest_tz.localize(datetime(2017, 10, 29, 2, 0), is_dst=True)
        self.travel.save()

        # Same date as the previous, but it's already after daylight saving
        start_date = budapest_tz.localize(datetime(2017, 10, 29, 2, 0), is_dst=False).isoformat()

        currency = CurrencyFactory()
        dsa_region = DSARegionFactory()

        data = {'deductions': [],
                'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14T17:06:55.821490',
                               'arrival_date': '2017-04-15T17:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20T12:06:55.821490',
                               'arrival_date': '2017-05-21T12:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'activities': [],
                'cost_assignments': [],
                'clearances': {'medical_clearance': 'requested',
                               'security_clearance': 'requested',
                               'security_course': 'requested'},
                'ta_required': True,
                'international_travel': False,
                'mode_of_travel': [ModeOfTravel.BOAT],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'start_date': start_date,
                'end_date': '2017-05-22T15:02:13+00:00',
                'currency': currency.id,
                'purpose': 'Purpose',
                'additional_note': 'Notes'}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.traveler)
        self.assertEqual(response.status_code, 201)
