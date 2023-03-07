from collections import defaultdict

from django.core.cache import cache
from django.utils.translation import gettext as _

from etools.applications.t2f.permission_action_points import action_points
from etools.applications.t2f.permissions import permissions

PERMISSION_MATRIX_CACHE_KEY = 't2f_permission_matrix'

REPORT_PERMISSIONS = {
    'Supervisor': {
        'completed': {'edit': False, 'view': True},
        'rejected': {'edit': False, 'view': True},
        'planned': {'edit': False, 'view': True},
        'submitted': {'edit': False, 'view': True},
        'cancelled': {'edit': False, 'view': True},
        'approved': {'edit': False, 'view': True}
    },
    'Finance Focal Point': {
        'completed': {'edit': False, 'view': True},
        'rejected': {'edit': False, 'view': True},
        'planned': {'edit': False, 'view': True},
        'submitted': {'edit': False, 'view': True},
        'cancelled': {'edit': False, 'view': True},
        'approved': {'edit': False, 'view': True}
    },
    'God': {
        'completed': {'edit': True, 'view': True},
        'rejected': {'edit': True, 'view': True},
        'planned': {'edit': True, 'view': True},
        'submitted': {'edit': True, 'view': True},
        'cancelled': {'edit': True, 'view': True},
        'approved': {'edit': True, 'view': True}
    },
    'Anyone': {
        'completed': {'edit': False, 'view': True},
        'rejected': {'edit': False, 'view': True},
        'planned': {'edit': False, 'view': True},
        'submitted': {'edit': False, 'view': True},
        'cancelled': {'edit': False, 'view': True},
        'approved': {'edit': False, 'view': True}
    },
    'Representative': {
        'completed': {'edit': False, 'view': True},
        'rejected': {'edit': False, 'view': True},
        'planned': {'edit': False, 'view': True},
        'submitted': {'edit': False, 'view': True},
        'cancelled': {'edit': False, 'view': True},
        'approved': {'edit': False, 'view': True}
    },
    'Travel Focal Point': {
        'completed': {'edit': False, 'view': True},
        'rejected': {'edit': False, 'view': True},
        'planned': {'edit': False, 'view': True},
        'submitted': {'edit': False, 'view': True},
        'cancelled': {'edit': False, 'view': True},
        'approved': {'edit': False, 'view': True}
    },
    'Traveler': {
        'completed': {'edit': False, 'view': True},
        'rejected': {'edit': True, 'view': True},
        'planned': {'edit': True, 'view': True},
        'submitted': {'edit': True, 'view': True},
        'cancelled': {'edit': False, 'view': True},
        'approved': {'edit': True, 'view': True}
    },
    'Travel Administrator': {
        'completed': {'edit': False, 'view': True},
        'rejected': {'edit': True, 'view': True},
        'planned': {'edit': True, 'view': True},
        'submitted': {'edit': True, 'view': True},
        'cancelled': {'edit': False, 'view': True},
        'approved': {'edit': False, 'view': True}
    }
}


class UserTypes:
    ANYONE = 'Anyone'
    TRAVELER = 'Traveler'
    TRAVEL_ADMINISTRATOR = 'Travel Administrator'
    SUPERVISOR = 'Supervisor'
    TRAVEL_FOCAL_POINT = 'Travel Focal Point'
    FINANCE_FOCAL_POINT = 'Finance Focal Point'
    REPRESENTATIVE = 'Representative'

    CHOICES = (
        (ANYONE, _('Anyone')),
        (TRAVELER, _('Traveler')),
        (TRAVEL_ADMINISTRATOR, _('Travel Administrator')),
        (SUPERVISOR, _('Supervisor')),
        (TRAVEL_FOCAL_POINT, _('Travel Focal Point')),
        (FINANCE_FOCAL_POINT, _('Finance Focal Point')),
        (REPRESENTATIVE, _('Representative')),
    )


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
                    data[model] = {
                        field: {action: perm},
                        action: perm,
                        "edit" if action == "view" else "view": False,
                    }
                else:
                    if field not in data[model]:
                        data[model][field] = {action: perm}
                    else:
                        data[model][field][action] = perm
                    if perm:
                        data[model][action] = perm
            to_format[user][state] = data
            # add report model permissions
            to_format[user][state]["report"] = REPORT_PERMISSIONS[user][state]
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


class PermissionMatrix:
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
