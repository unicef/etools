import json

from StringIO import StringIO
from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from et2f import TripStatus, UserTypes
from et2f.models import TravelPermission, DSARegion, AirlineCompany, Travel, TravelAttachment
from et2f.tests.factories import AirlineCompanyFactory

from .factories import TravelFactory


class TravelViews(APITenantTestCase):
    maxDiff = None

    def setUp(self):
        super(TravelViews, self).setUp()
        self.traveller = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(reference_number='REF1',
                                    traveller=self.traveller,
                                    supervisor=self.unicef_staff)

    def test_list_view(self):
        response = self.forced_auth_req('get', '/api/et2f/travels/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 1)
        self.assertIn('page_count', response_json)
        self.assertEqual(response_json['page_count'], 1)

    def test_pagination(self):
        TravelFactory(traveller=self.traveller, supervisor=self.unicef_staff)
        TravelFactory(traveller=self.traveller, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'page': 1, 'page_size': 2},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 2)
        self.assertIn('page_count', response_json)
        self.assertEqual(response_json['page_count'], 2)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'page': 2, 'page_size': 2},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 1)

    def test_sorting(self):
        TravelFactory(reference_number='ref2', traveller=self.traveller, supervisor=self.unicef_staff)
        TravelFactory(reference_number='REF3', traveller=self.traveller, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'sort_by': 'reference_number',
                                                                           'reverse': False},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        reference_numbers = [e['reference_number'] for e in response_json['data']]
        self.assertEqual(reference_numbers, ['REF1', 'ref2', 'REF3'])

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'sort_by': 'reference_number',
                                                                           'reverse': True},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        reference_numbers = [e['reference_number'] for e in response_json['data']]
        self.assertEqual(reference_numbers, ['REF3', 'ref2', 'REF1'])

    def test_searching(self):
        TravelFactory(reference_number='REF2', traveller=self.traveller, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'search': 'REF2'},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 1)

    def test_show_hidden(self):
        TravelFactory(reference_number='REF2', traveller=self.traveller, supervisor=self.unicef_staff, hidden=True)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'show_hidden': True},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 2)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'show_hidden': False},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 1)

    def test_travel_creation(self):
        dsaregion = DSARegion.objects.first()
        airlines = AirlineCompanyFactory()
        airlines2 = AirlineCompanyFactory()

        data = {'cost_assignments': [],
                'deductions': [{'date': '2016-11-03',
                                'breakfast': True,
                                'lunch': True,
                                'dinner': False,
                                'accomodation': True}],
                'expenses': [],
                'itinerary': [{'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-16T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': 'plane',
                               'airlines': [airlines.id, airlines2.id]}],
                'activities': [],
                'start_date': '2016-11-15T12:06:55.821490',
                'end_date': '2016-11-17T12:06:55.821490'}
        response = self.forced_auth_req('post', '/api/et2f/travels/', data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        # self.assertEqual(response_json, {})

        t = Travel.objects.get(id=response_json['id'])
        self.assertEqual(t.cost_summary, {})

        # t = Travel.objects.get(id=response_json['id'])
        # t.cancel()
        # t.save()
        #
        # response = self.forced_auth_req('get', '/api/et2f/travels/{}/'.format(response_json['id']),
        #                                 user=self.unicef_staff)
        # response_json = json.loads(response.rendered_content)
        # self.assertEqual(response_json, {})
        #
        # response_json['deductions'].append({'date': '2016-12-12',
        #                                     'dinner': True,
        #                                     'lunch': True,
        #                                     'no_dsa': False})
        #
        # response = self.forced_auth_req('patch', '/api/et2f/travels/{}/'.format(response_json['id']),
        #                                 data=response_json,
        #                                 user=self.unicef_staff)
        # response_json = json.loads(response.rendered_content)
        # self.assertEqual(response_json, {})

    def test_static_data_endpoint(self):
        response = self.forced_auth_req('get', '/api/et2f/static_data/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {})

    def test_curent_user_endpoint(self):
        response = self.forced_auth_req('get', '/api/et2f/me/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {})


    def test_payload(self):
        TravelPermission.objects.create(name='afds', code='can_see_travel_status', user_type='God', status='planned')

        travel = TravelFactory()
        response = self.forced_auth_req('get', '/api/et2f/travels/{}/'.format(travel.id), user=self.unicef_staff)
        self.assertEqual(json.loads(response.rendered_content), {})

    def test_permission_matrix(self):
        model_field_mapping = {'clearances': ('id',
                                              'medical_clearance',
                                              'security_clearance',
                                              'security_course'),
                               'cost_assignments': ('id', 'wbs', 'share', 'grant'),
                               'deductions': ('id',
                                             'date',
                                             'breakfast',
                                             'lunch',
                                             'dinner',
                                             'accomodation',
                                             'no_dsa',
                                             'day_of_the_week'),
                               'expenses': ('id',
                                           'type',
                                           'document_currency',
                                           'account_currency',
                                           'amount'),
                               'itinerary': ('id',
                                                 'origin',
                                                 'destination',
                                                 'departure_date',
                                                 'arrival_date',
                                                 'dsa_region',
                                                 'overnight_travel',
                                                 'mode_of_travel',
                                                 'airlines'),
                               'travel': ('reference_number',
                                          'supervisor',
                                          'office',
                                          'end_date',
                                          'section',
                                          'international_travel',
                                          'traveller',
                                          'start_date',
                                          'ta_required',
                                          'purpose',
                                          'id',
                                          'itinerary',
                                          'expenses',
                                          'deductions',
                                          'cost_assignments',
                                          'clearances',
                                          'status',
                                          'activities',
                                          'mode_of_travel',
                                          'estimated_travel_cost',
                                          'currency'),
                               'activities': ('id',
                                                  'travel_type',
                                                  'partner',
                                                  'partnership',
                                                  'result',
                                                  'locations',
                                                  'primary_traveler',
                                                  'date')}


        permissions = []
        for user_type in UserTypes.CHOICES:
            for status in TripStatus.CHOICES:
                for model_name, fields in model_field_mapping.items():
                    for field_name in fields:
                        name = '_'.join((user_type[0], status[0], model_name, field_name, TravelPermission.EDIT))
                        kwargs = dict(name=name,
                                      user_type=user_type[0],
                                      status=status[0],
                                      model=model_name,
                                      field=field_name,
                                      permission_type=TravelPermission.EDIT,
                                      value=True)
                        permissions.append(TravelPermission(**kwargs))

                        name = '_'.join((user_type[0], status[0], model_name, field_name, TravelPermission.VIEW))
                        kwargs = dict(name=name,
                                      user_type=user_type[0],
                                      status=status[0],
                                      model=model_name,
                                      field=field_name,
                                      permission_type=TravelPermission.VIEW,
                                      value=True)
                        permissions.append(TravelPermission(**kwargs))

        TravelPermission.objects.bulk_create(permissions)

        response = self.forced_auth_req('get', '/api/et2f/permission_matrix/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        from pprint import pformat

        with open('ki.json', 'w') as out:
            out.write(pformat(response_json))

    # def test_permission_matrix(self):
    #     from et2f.serializers import IteneraryItemSerializer, ExpenseSerializer, DeductionSerializer, \
    #         CostAssignmentSerializer, ClearancesSerializer, TravelActivitySerializer, TravelDetailsSerializer
    #
    #     serializers = (
    #         IteneraryItemSerializer,
    #         ExpenseSerializer,
    #         DeductionSerializer,
    #         CostAssignmentSerializer,
    #         ClearancesSerializer,
    #         TravelActivitySerializer,
    #         TravelDetailsSerializer)
    #
    #     permnames = {}
    #     for s in serializers:
    #         model_name = s.Meta.model.__name__.lower()
    #         fields = s.Meta.fields
    #         permnames[model_name] = fields
    #
    #     self.assertEqual(permnames, {})

    def test_file_attachments(self):
        class FakeFile(StringIO):
            def size(self):
                return len(self)

        fakefile = FakeFile('some stuff')
        travel = TravelFactory()
        attachment = TravelAttachment.objects.create(travel=travel,
                                                     name='Lofasz',
                                                     type='nehogymar')
        attachment.file.save('fake.txt', fakefile)
        fakefile.seek(0)

        data = {'name': 'second',
                'type': 'something',
                'file': fakefile}
        response = self.forced_auth_req('post', '/api/et2f/travels/{}/attachments/'.format(travel.id), data=data,
                                        user=self.unicef_staff, request_format='multipart')
        response_json = json.loads(response.rendered_content)
        # self.assertEqual(response_json, {})

        response = self.forced_auth_req('delete',
                                        '/api/et2f/travels/{}/attachments/{}/'.format(travel.id, response_json['id']),
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 0)

    def test_duplication(self):
        response = self.forced_auth_req('post', '/api/et2f/travels/{}/add_driver/'.format(self.travel.id),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {})