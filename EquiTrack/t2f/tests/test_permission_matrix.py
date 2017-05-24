from __future__ import unicode_literals

import mock
from django.contrib.auth.models import Group

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from t2f import UserTypes
from t2f.helpers.permission_matrix import PermissionMatrix, get_user_role_list
from t2f.models import Travel

from .factories import TravelFactory


class TestPermissionMatrix(APITenantTestCase):
    def setUp(self):
        super(TestPermissionMatrix, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)

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

    @mock.patch('t2f.helpers.permission_matrix.get_permission_matrix')
    def test_permission_aggregation(self, permission_matrix_getter):
        permission_matrix_getter.return_value = {'travel':
                                                     {UserTypes.TRAVELER:
                                                          {Travel.PLANNED:
                                                               {'baseDetails':
                                                                    {'ta_required':
                                                                         {'edit': True,
                                                                          'view': True}}}},
                                                      UserTypes.SUPERVISOR:
                                                          {Travel.PLANNED:
                                                               {'baseDetails':
                                                                    {'ta_required':
                                                                         {'edit': False,
                                                                          'view': True}}}}}}

        travel = TravelFactory(traveler=self.traveler,
                               supervisor=self.unicef_staff)

        # Check traveler
        permission_matrix = PermissionMatrix(travel, self.traveler)
        permissions = permission_matrix.get_permission_dict()
        self.assertEqual(dict(permissions),
                         {('travel', 'ta_required', 'edit'): True,
                          ('travel', 'ta_required', 'view'): True})

        # Check supervisor
        permission_matrix = PermissionMatrix(travel, self.unicef_staff)
        permissions = permission_matrix.get_permission_dict()
        self.assertEqual(dict(permissions),
                         {('travel', 'ta_required', 'edit'): False,
                          ('travel', 'ta_required', 'view'): True})

        travel = TravelFactory(traveler=self.traveler,
                               supervisor=self.traveler)
        # Check both the same time (not really possible, but good to check aggregation)
        permission_matrix = PermissionMatrix(travel, self.traveler)
        permissions = permission_matrix.get_permission_dict()
        self.assertEqual(dict(permissions),
                         {('travel', 'ta_required', 'edit'): True,
                          ('travel', 'ta_required', 'view'): True})
