
import json
import logging
from datetime import datetime

from django.core.urlresolvers import reverse

import pytz
from freezegun import freeze_time
from pytz import UTC

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.publics.tests.factories import (PublicsBusinessAreaFactory, PublicsCurrencyFactory,
                                                         PublicsDSARateFactory, PublicsDSARegionFactory,
                                                         PublicsTravelExpenseTypeFactory,)
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
                                   start_date=datetime(2017, 4, 4, 12, 00, tzinfo=UTC),
                                   end_date=datetime(2017, 4, 14, 16, 00, tzinfo=UTC))
        cls.travel.expenses.all().delete()
        ItineraryItemFactory(travel=cls.travel)
        ItineraryItemFactory(travel=cls.travel)
        cls.travel.submit_for_approval()
        cls.travel.approve()
        cls.travel.send_for_payment()
        cls.travel.save()

    def test_overlapping_trips(self):
        currency = PublicsCurrencyFactory()
        dsa_region = PublicsDSARegionFactory()

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
        currency = PublicsCurrencyFactory()
        expense_type = PublicsTravelExpenseTypeFactory()
        dsa_rate = PublicsDSARateFactory(effective_from_date=datetime(2017, 4, 10, 16, 00, tzinfo=UTC))
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
        currency = PublicsCurrencyFactory()
        dsa_region = PublicsDSARegionFactory()

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
            {
                'origin': 'Berlin',
                'destination': 'Budapest',
                'departure_date': '2017-04-10T16:05:00+00:00',
                'arrival_date': '2017-04-15T17:06:55.821490',
                'dsa_region': dsa_region.id,
                'overnight_travel': False,
                'mode_of_travel': ModeOfTravel.RAIL,
                'airlines': []
            },
            {
                'origin': 'Budapest',
                'destination': 'Berlin',
                'departure_date': '2017-05-20T12:06:55.821490',
                'arrival_date': '2017-05-21T12:06:55.821490',
                'dsa_region': dsa_region.id,
                'overnight_travel': False,
                'mode_of_travel': ModeOfTravel.RAIL,
                'airlines': []
            }
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

        currency = PublicsCurrencyFactory()
        dsa_region = PublicsDSARegionFactory()

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
