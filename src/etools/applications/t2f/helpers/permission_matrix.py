from collections import defaultdict

from django.core.cache import cache

from etools.applications.t2f import UserTypes
from etools.applications.t2f.action_points import action_points
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


def convert_permissions_structure():
    """Convert permissions from
    (edit/view, model, field) | permission
    to
    model | field | edit/view | permission
    """
    to_format = {}
    for user, states in permissions.items():
        to_format[user] = {}
        for state, actions in states.items():
            data = defaultdict(dict)
            for key, perm in actions.items():
                action, model, field = key
                model = "baseDetails" if model == "travel" else model
                if model not in data:
                    data[model] = {field: {action: perm}}
                else:
                    if field not in data[model]:
                        data[model][field] = {action: perm}
                    else:
                        data[model][field][action] = perm
            to_format[user][state] = data
    return to_format


def get_permission_matrix():
    permission_matrix = cache.get(PERMISSION_MATRIX_CACHE_KEY)
    if not permission_matrix:
        permission_matrix = {
            "action_point": action_points,
            "travel": convert_permissions_structure()
        }
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
