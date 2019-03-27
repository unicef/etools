import json
import os
import pprint
from collections import defaultdict

from django.core.cache import cache

import yaml

from etools.applications import t2f
from etools.applications.t2f import UserTypes
from etools.applications.t2f.models import Travel
from etools.applications.t2f.permissions import permissions

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
        path = os.path.join(
            os.path.dirname(t2f.__file__),
            "permission_matrix.json",
        )

        with open(path) as permission_matrix_file:
            permission_matrix = json.loads(permission_matrix_file.read())
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
        perms = defaultdict(bool)
        for user_type in self._user_roles:
            try:
                for k, v in permissions[user_type][self.travel.status].items():
                    perms[k] |= v
            except KeyError:
                pass

        return perms

    def has_permission(self, permission_type, model_name, field_name):
        return self._permission_dict.get((permission_type, model_name, field_name), True)


class FakePermissionMatrix(PermissionMatrix):
    def __init__(self, user):
        super().__init__(None, user)

    def has_permission(self, permission_type, model_name, field_name):
        return True

    def get_permission_dict(self):
        return {}
