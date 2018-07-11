
import json
import logging

from django.core.urlresolvers import NoReverseMatch, reverse
from django.db import connection

from freezegun import freeze_time
from rest_framework import status

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.EquiTrack.tests.mixins import URLAssertionMixin
from etools.applications.locations.tests.factories import LocationFactory
from etools.applications.publics.models import DSARegion
from etools.applications.publics.tests.factories import PublicsCurrencyFactory, PublicsWBSFactory
from etools.applications.reports.tests.factories import ResultFactory
from etools.applications.t2f.models import make_travel_reference_number, ModeOfTravel, Travel, TravelType
from etools.applications.t2f.tests.factories import TravelActivityFactory, TravelFactory
from etools.applications.users.tests.factories import UserFactory

log = logging.getLogger('__name__')


class TravelList(URLAssertionMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.traveler = UserFactory()
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.travel = TravelFactory(reference_number=make_travel_reference_number(),
                                   traveler=cls.traveler,
                                   supervisor=cls.unicef_staff)

    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('index', '', {}),
            ('state_change', 'save_and_submit/', {'transition_name': 'save_and_submit'}),
            ('state_change', 'mark_as_completed/', {'transition_name': 'mark_as_completed'}),
            ('activity_export', 'export/', {}),
            ('finance_export', 'finance-export/', {}),
            ('travel_admin_export', 'travel-admin-export/', {}),
            ('invoice_export', 'invoice-export/', {}),
            ('activities', 'activities/1/', {'partner_organization_pk': 1}),
            ('activities-intervention', 'activities/partnership/1/', {'partnership_pk': 1}),
            ('dashboard', 'dashboard', {}),
        )
        self.assertReversal(names_and_paths, 't2f:travels:list:', '/api/t2f/travels/')
        self.assertIntParamRegexes(names_and_paths, 't2f:travels:list:')

        # Exercise dashboard to ensure year and month regexes only accept 4- and 2-digit int args, respectively.
        for invalid_year in (1, '1', '123', '12345', '123x', 'x123', 'xxxx', ):
            with self.assertRaises(NoReverseMatch):
                reverse('t2f:travels:list:dashboard?year={}'.format(invalid_year), kwargs={})

        for invalid_month in (1, '1', '007', '4x', 'x4', 'xx', ):
            with self.assertRaises(NoReverseMatch):
                reverse('t2f:travels:list:dashboard?year=2017&months={}'.format(invalid_month), kwargs={})

    def test_list_view(self):
        with self.assertNumQueries(5):
            response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        expected_keys = ['data', 'page_count', 'total_count']
        self.assertKeysIn(expected_keys, response_json)

        self.assertEqual(len(response_json['data']), 1)
        travel_data = response_json['data'][0]
        expected_keys = ['end_date', 'id', 'office', 'purpose', 'reference_number', 'start_date', 'status', 'traveler']
        self.assertKeysIn(expected_keys, travel_data)

    def test_list_search_partial(self):
        response = self.forced_auth_req(
            'get',
            reverse('t2f:travels:list:index'),
            data={'reference_number': self.travel.reference_number[2:5]},
            user=self.unicef_staff
        )

        response_json = json.loads(response.rendered_content)
        expected_keys = ['data', 'page_count', 'total_count']
        self.assertKeysIn(expected_keys, response_json)
        self.assertEqual(len(response_json['data']), 1)

    def test_dashboard_travels_list_view(self):
        with self.assertNumQueries(10):
            response = self.forced_auth_req(
                'get',
                reverse(
                    't2f:travels:list:dashboard',
                ),
                user=self.unicef_staff,
                data={
                    "office_id": self.travel.office.id,
                    "year": self.travel.start_date.year,
                    "months": '{month:02d}'.format(month=self.travel.start_date.month)
                }
            )

        response_json = json.loads(response.rendered_content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_keys = ['travels_by_section', 'completed', 'planned', 'approved']
        self.assertKeysIn(expected_keys, response_json)
        self.assertEqual(len(response_json['travels_by_section']), 1)
        self.assertEqual(response_json['planned'], 1)

    def test_dashboard_travels_list_view_no_section(self):
        travel = TravelFactory(reference_number=make_travel_reference_number(),
                               traveler=self.traveler,
                               supervisor=self.unicef_staff,
                               section=None)

        with self.assertNumQueries(10):
            response = self.forced_auth_req(
                'get',
                reverse(
                    't2f:travels:list:dashboard',

                ),
                user=self.unicef_staff,
                data={
                    "office_id": travel.office.id,
                    "year": travel.start_date.year,
                    "months": '{month:02d}'.format(month=travel.start_date.month)
                }
            )

        response_json = json.loads(response.rendered_content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_keys = ['travels_by_section', 'completed', 'planned', 'approved']
        self.assertKeysIn(expected_keys, response_json)
        self.assertEqual(response_json['travels_by_section'][0]['section_name'], 'No Section selected')
        self.assertEqual(len(response_json['travels_by_section']), 1)
        self.assertEqual(response_json['planned'], 1)

    def test_dashboard_action_points_list_view(self):
        with self.assertNumQueries(6):
            response = self.forced_auth_req(
                'get',
                reverse('t2f:action_points:dashboard'),
                user=self.unicef_staff,
                data={"office_id": self.travel.office.id}
            )

        response_json = json.loads(response.rendered_content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_keys = ['action_points_by_section']
        self.assertKeysIn(expected_keys, response_json)
        self.assertEqual(len(response_json['action_points_by_section']), 1)
        self.assertEqual(response_json['action_points_by_section'][0]['total_action_points'], 1)

    def test_dashboard_action_points_list_view_no_office(self):
        with self.assertNumQueries(6):
            response = self.forced_auth_req(
                'get',
                reverse('t2f:action_points:dashboard'),
                user=self.unicef_staff,
            )

        response_json = json.loads(response.rendered_content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_keys = ['action_points_by_section']
        self.assertKeysIn(expected_keys, response_json)
        self.assertEqual(len(response_json['action_points_by_section']), 1)
        self.assertEqual(response_json['action_points_by_section'][0]['total_action_points'], 1)

    def test_pagination(self):
        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'page': 1, 'page_size': 2},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 2)
        self.assertIn('page_count', response_json)
        self.assertEqual(response_json['page_count'], 2)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'page': 2, 'page_size': 2},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 1)

    @freeze_time('2016-12-14')
    def test_sorting(self):
        # Travels have to be deleted here to avoid reference numbers generated ouf of the desired time range
        # (setUp is not covered by the freezegun decorator)
        Travel.objects.all().delete()
        counters = connection.tenant.counters
        counters.travel_reference_number_counter = 1
        counters.save()

        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'sort_by': 'reference_number',
                                                                                        'reverse': False},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        reference_numbers = [e['reference_number'] for e in response_json['data']]
        self.assertEqual(reference_numbers, ['2016/1', '2016/2', '2016/3'])

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'sort_by': 'reference_number',
                                                                                        'reverse': True},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        reference_numbers = [e['reference_number'] for e in response_json['data']]
        self.assertEqual(reference_numbers, ['2016/3', '2016/2', '2016/1'])

        # Here just iterate over the possible fields and do all the combinations of sorting
        # to see if all works (non-500)
        possible_sort_options = response_json['data'][0].keys()
        for sort_option in possible_sort_options:
            log.debug(u'Trying to sort by %s', sort_option)
            self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'sort_by': sort_option,
                                                                                 'reverse': False},
                                 user=self.unicef_staff)

    def test_filtering(self):
        t1 = TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        a1 = TravelActivityFactory(travel_type=TravelType.MEETING, primary_traveler=self.unicef_staff)
        a1.travels.add(t1)

        t2 = TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        a2 = TravelActivityFactory(travel_type=TravelType.PROGRAMME_MONITORING, primary_traveler=self.unicef_staff)
        a2.travels.add(t2)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'),
                                        data={'f_travel_type': TravelType.MEETING},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 1)

    def test_filtering_options(self):
        t1 = TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        a1 = TravelActivityFactory(travel_type=TravelType.MEETING, primary_traveler=self.unicef_staff)
        a1.travels.add(t1)

        result = ResultFactory()
        t2 = TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        a2 = TravelActivityFactory(
            travel_type=TravelType.PROGRAMME_MONITORING,
            primary_traveler=self.unicef_staff,
            result=result
        )
        a2.travels.add(t2)

        data = {
            'f_travel_type': TravelType.PROGRAMME_MONITORING,
            'f_month': t2.start_date.month - 1,  # Frontend sends 0-11
            'f_cp_output': result.id,
        }
        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 1)
        self.assertEqual(response_json['data'][0]['id'], t2.id)

    def test_searching(self):
        travel = TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'),
                                        data={'search': travel.reference_number},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 1)

    def test_show_hidden(self):
        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff, hidden=True)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'show_hidden': True},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 2)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'show_hidden': False},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 1)

    def test_travel_creation(self):
        dsaregion = DSARegion.objects.first()
        currency = PublicsCurrencyFactory()
        wbs = PublicsWBSFactory()
        grant = wbs.grants.first()
        fund = grant.funds.first()
        location = LocationFactory()

        data = {'0': {},
                '1': {'date': '2016-12-16',
                      'breakfast': False,
                      'lunch': False,
                      'dinner': False,
                      'accomodation': False,
                      'no_dsa': False},
                'deductions': [{'date': '2016-12-15',
                                'breakfast': False,
                                'lunch': False,
                                'dinner': False,
                                'accomodation': False,
                                'no_dsa': False},
                               {'date': '2016-12-16',
                                'breakfast': False,
                                'lunch': False,
                                'dinner': False,
                                'accomodation': False,
                                'no_dsa': False}],
                'itinerary': [{'airlines': [],
                               'overnight_travel': False,
                               'origin': 'a',
                               'destination': 'b',
                               'dsa_region': dsaregion.id,
                               'departure_date': '2016-12-15T15:02:13+01:00',
                               'arrival_date': '2016-12-16T15:02:13+01:00',
                               'mode_of_travel': ModeOfTravel.BOAT}],
                'activities': [{'is_primary_traveler': True,
                                'locations': [location.id],
                                'travel_type': TravelType.ADVOCACY,
                                'date': '2016-12-15T15:02:13+01:00'}],
                'cost_assignments': [{'wbs': wbs.id,
                                      'grant': grant.id,
                                      'fund': fund.id,
                                      'share': '100'}],
                'clearances': {'medical_clearance': 'requested',
                               'security_clearance': 'requested',
                               'security_course': 'requested'},
                'ta_required': True,
                'international_travel': False,
                'mode_of_travel': [ModeOfTravel.BOAT],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'start_date': '2016-12-15T15:02:13+01:00',
                'end_date': '2016-12-16T15:02:13+01:00',
                'estimated_travel_cost': '123',
                'currency': currency.id,
                'purpose': 'Purpose',
                'additional_note': 'Notes',
                'medical_clearance': 'requested',
                'security_clearance': 'requested',
                'security_course': 'requested'}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['itinerary']), 1)
