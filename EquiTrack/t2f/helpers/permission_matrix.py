from __future__ import unicode_literals

import os
from collections import defaultdict

import yaml
from django.conf import settings
from django.core.cache import cache

from t2f import UserTypes

PERMISSION_MATRIX_CACHE_KEY = 't2f_permission_matrix'


def get_user_role_list(user, travel=None):
    roles = [UserTypes.ANYONE]

    if travel:
        if user == travel.traveler:
            roles.append(UserTypes.TRAVELER)

        if user == travel.supervisor:
            roles.append(UserTypes.SUPERVISOR)

    if user.groups.filter(name='Finance Focal Point').exists():
        roles.append(UserTypes.FINANCE_FOCAL_POINT)

    if user.groups.filter(name='Travel Focal Point').exists():
        roles.append(UserTypes.TRAVEL_FOCAL_POINT)

    if user.groups.filter(name='Travel Administrator').exists():
        roles.append(UserTypes.TRAVEL_ADMINISTRATOR)

    if user.groups.filter(name='Representative Office').exists():
        roles.append(UserTypes.REPRESENTATIVE)

    return roles


def get_permission_matrix():
    permission_matrix = cache.get(PERMISSION_MATRIX_CACHE_KEY)
    if not permission_matrix:
        path = os.path.join(settings.SITE_ROOT, 't2f', 'permission_matrix.yaml')

        with open(path) as permission_matrix_file:
            permission_matrix = yaml.load(permission_matrix_file.read())
        cache.set(PERMISSION_MATRIX_CACHE_KEY, permission_matrix)

    return permission_matrix


class PermissionMatrix(object):
    VIEW = 'view'
    EDIT = 'edit'

    def __init__(self, travel, user):
        self.travel = travel
        self.user = user
        self._user_roles = get_user_role_list(user, travel)
        self._permission_dict = self.get_permission_dict()

    def get_permission_dict(self):
        permission_matrix = get_permission_matrix()['travel']

        permissions = defaultdict(bool)
        for user_type, um in permission_matrix.items():
            if user_type not in self._user_roles:
                continue

            for state, sm in um.items():
                if state != self.travel.status:
                    continue

                for model, mm in sm.items():
                    if model == 'baseDetails':
                        model = 'travel'

                    for field, fm in mm.items():
                        if not isinstance(fm, dict):
                            permissions[(field, 'travel', model)] |= fm
                            continue

                        for permission_type, value in fm.items():
                            permissions[(permission_type, model, field, )] |= value

        return permissions

    def has_permission(self, permission_type, model_name, field_name):
        return self._permission_dict.get((permission_type, model_name, field_name), True)


class FakePermissionMatrix(PermissionMatrix):
    def __init__(self, user):
        super(FakePermissionMatrix, self).__init__(None, user)

    def has_permission(self, permission_type, model_name, field_name):
        return True

    def get_permission_dict(self):
        return {}
