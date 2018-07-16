
import json

from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse

import mock

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from unicef_locations.tests.factories import LocationFactory
from etools.applications.publics.tests.factories import (PublicsCurrencyFactory,
                                                         PublicsDSARegionFactory, PublicsWBSFactory,)
from etools.applications.t2f import UserTypes
from etools.applications.t2f.helpers.permission_matrix import get_user_role_list, PermissionMatrix
from etools.applications.t2f.models import ModeOfTravel, Travel, TravelType
from etools.applications.t2f.tests.factories import TravelFactory
from etools.applications.users.tests.factories import UserFactory


class TestPermissionMatrix(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.traveler = UserFactory(is_staff=True)
        cls.unicef_staff = UserFactory(is_staff=True)

    def test_urls(self):
        list_url = reverse('t2f:permission_matrix')
        self.assertEqual(list_url, '/api/t2f/permission_matrix/')

    def test_permission_matrix(self):
        # Check the effect of caching
        with self.assertNumQueries(0):
            self.forced_auth_req('get', reverse('t2f:permission_matrix'), user=self.unicef_staff)

        with self.assertNumQueries(0):
            self.forced_auth_req('get', reverse('t2f:permission_matrix'), user=self.unicef_staff)

    def test_user_type_lookup(self):
        travel = TravelFactory(traveler=self.traveler,
                               supervisor=self.unicef_staff)

        group_tfp = Group.objects.create(name='Travel Focal Point')
        group_ffp = Group.objects.create(name='Finance Focal Point')
        group_ta = Group.objects.create(name='Travel Administrator')
        group_representative = Group.objects.create(name='Representative Office')

        just_a_user = UserFactory()

        ffp = UserFactory()
        ffp.groups.add(group_ffp)

        tfp = UserFactory()
        tfp.groups.add(group_tfp)

        ta = UserFactory()
        ta.groups.add(group_ta)

        representative = UserFactory()
        representative.groups.add(group_representative)

        roles = get_user_role_list(just_a_user, travel)
        self.assertEqual(roles, [UserTypes.ANYONE])

        roles = get_user_role_list(self.traveler, travel)
        self.assertEqual(roles, [UserTypes.ANYONE,
                                 UserTypes.TRAVELER])

        roles = get_user_role_list(self.unicef_staff, travel)
        self.assertEqual(roles, [UserTypes.ANYONE,
                                 UserTypes.SUPERVISOR])

        roles = get_user_role_list(ffp, travel)
        self.assertEqual(roles, [UserTypes.ANYONE,
                                 UserTypes.FINANCE_FOCAL_POINT])

        roles = get_user_role_list(tfp, travel)
        self.assertEqual(roles, [UserTypes.ANYONE,
                                 UserTypes.TRAVEL_FOCAL_POINT])

        roles = get_user_role_list(ta, travel)
        self.assertEqual(roles, [UserTypes.ANYONE,
                                 UserTypes.TRAVEL_ADMINISTRATOR])

        roles = get_user_role_list(representative, travel)
        self.assertEqual(roles, [UserTypes.ANYONE,
                                 UserTypes.REPRESENTATIVE])

        # Test and all in user
        all_in_superuser = UserFactory()
        all_in_superuser.groups.add(group_ffp, group_tfp, group_ta, group_representative)

        travel = TravelFactory(traveler=all_in_superuser,
                               supervisor=all_in_superuser)
        roles = get_user_role_list(all_in_superuser, travel)
        self.assertEqual(roles, [UserTypes.ANYONE,
                                 UserTypes.TRAVELER,
                                 UserTypes.SUPERVISOR,
                                 UserTypes.FINANCE_FOCAL_POINT,
                                 UserTypes.TRAVEL_FOCAL_POINT,
                                 UserTypes.TRAVEL_ADMINISTRATOR,
                                 UserTypes.REPRESENTATIVE])

    @mock.patch('etools.applications.t2f.helpers.permission_matrix.get_permission_matrix')
    def test_permission_aggregation(self, permission_matrix_getter):
        permission_matrix_getter.return_value = {
            'travel': {
                UserTypes.TRAVELER: {
                    Travel.PLANNED: {
                        'baseDetails': {
                            'ta_required': {
                                'edit': True,
                                'view': True}}}},
                UserTypes.SUPERVISOR: {
                    Travel.PLANNED: {
                        'baseDetails': {
                            'ta_required': {
                                'edit': False,
                                'view': True}}}}}}

        travel = TravelFactory(traveler=self.traveler,
                               supervisor=self.unicef_staff)

        # Check traveler
        permission_matrix = PermissionMatrix(travel, self.traveler)
        permissions = permission_matrix.get_permission_dict()
        self.assertEqual(dict(permissions),
                         {('edit', 'travel', 'ta_required'): True,
                          ('view', 'travel', 'ta_required'): True})

        # Check supervisor
        permission_matrix = PermissionMatrix(travel, self.unicef_staff)
        permissions = permission_matrix.get_permission_dict()
        self.assertEqual(dict(permissions),
                         {('edit', 'travel', 'ta_required'): False,
                          ('view', 'travel', 'ta_required'): True})

        travel = TravelFactory(traveler=self.traveler,
                               supervisor=self.traveler)
        # Check both the same time (not really possible, but good to check aggregation)
        permission_matrix = PermissionMatrix(travel, self.traveler)
        permissions = permission_matrix.get_permission_dict()
        self.assertEqual(dict(permissions),
                         {('edit', 'travel', 'ta_required'): True,
                          ('view', 'travel', 'ta_required'): True})

    def test_travel_creation(self):
        dsa_region = PublicsDSARegionFactory()
        currency = PublicsCurrencyFactory()
        wbs = PublicsWBSFactory()
        grant = wbs.grants.first()
        fund = grant.funds.first()
        location = LocationFactory()

        purpose = 'Some purpose to check later'

        data = {'deductions': [{'date': '2016-12-15',
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
                'purpose': purpose,
                'additional_note': 'Notes',
                'medical_clearance': 'requested',
                'security_clearance': 'requested',
                'security_course': 'requested'}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                        kwargs={'transition_name': 'save_and_submit'}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['purpose'], purpose)
        self.assertEqual(response_json['status'], Travel.SUBMITTED)
        travel_id = response_json['id']

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['status'], Travel.APPROVED)

        data = {'purpose': 'Some totally different purpose than before'}
        response = self.forced_auth_req('patch', reverse('t2f:travels:details:index',
                                                         kwargs={'travel_pk': response_json['id']}),
                                        data=data, user=self.traveler)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['purpose'], purpose)
