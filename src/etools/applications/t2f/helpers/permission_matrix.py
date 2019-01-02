import json
import os
import pprint
from collections import defaultdict

from django.core.cache import cache

import yaml

from etools.applications import t2f
from etools.applications.t2f import UserTypes
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
        path = os.path.join(os.path.dirname(t2f.__file__), "permission_matrix.json")

        with open(path) as permission_matrix_file:
            permission_matrix = json.loads(permission_matrix_file.read())
        cache.set(PERMISSION_MATRIX_CACHE_KEY, permission_matrix)

    return permission_matrix


def get_permission_matrix_old():
    path = os.path.join(os.path.dirname(t2f.__file__), "permission_matrix.yaml")
    with open(path) as permission_matrix_file:
        permission_matrix = yaml.load(permission_matrix_file.read())
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


def parse_permission_matrix():
    """Extra data from permission_matrix

    Default expected permission is;
    - `edit`: False
    - `view`: True

    For each record check if it is different to the default
    if so, take note

    Structure of permission_matrix is;
    Travel: {
       "User": {
         "Status": {
           "Model": {
             "edit": ...,
             "view": ...,
             "<field_name>": {
               "edit": ...,
               "view": ...,
             },
           },
         },
      },
    }
    """
    def machine_readable(data):
        # display results in machine readable format
        # d = {"user": {"status": {"model": {"field": {"perm": "value"}}}}}
        result = {}
        for user_type, states in data.items():
            result[user_type] = {}
            for state, models in states.items():
                result[user_type][state] = defaultdict(bool)
                for model, fields in models.items():
                    for field, perm_types in fields.items():
                        for perm_type, perm in perm_types.items():
                            if field == "all":
                                key = (perm_type, "travel", model)
                            else:
                                key = (perm_type, model, field)
                            result[user_type][state][key] |= perm

        pp = pprint.PrettyPrinter(indent=4)
        with open("travel_permissions.py", "w") as fp:
            fp.write("permissions = {}".format(
                pp.pformat(result).replace(
                    "defaultdict(<class 'bool'>,", ""
                ).replace(
                    "})", "}"
                )
            ))

    matrix = get_permission_matrix_old()
    model_fields = defaultdict(set)
    results = {}
    for user in matrix["travel"]:
        data = {}
        for status in matrix["travel"][user]:
            data[status] = defaultdict()
            for model in matrix["travel"][user][status]:
                model_key = "travel" if model == "baseDetails" else model
                data[status][model_key] = defaultdict(dict)
                for field in matrix["travel"][user][status][model]:
                    # get a list of all fields for the model
                    model_fields[model_key].add("all" if field in ["edit", "view"] else field)

                    perm_dict = matrix["travel"][user][status][model][field]
                    if field in ["edit", "view"]:
                        data[status][model_key]["all"][field] = perm_dict
                    else:
                        for perm in ["edit", "view"]:
                            perm_value = perm_dict[perm]
                            data[status][model_key][field][perm] = perm_value
        results[user] = data

    machine_readable(results)


def convert_matrix_to_json():
    """Take old permission matrix in yaml format and convert to json"""
    matrix = get_permission_matrix_old()
    path = os.path.join(os.path.dirname(t2f.__file__), "permission_matrix.json")

    with open(path, "w") as fp:
        fp.write(json.dumps(matrix))
