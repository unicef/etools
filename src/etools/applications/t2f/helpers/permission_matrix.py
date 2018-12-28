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
        path = os.path.join(os.path.dirname(t2f.__file__), "permission_matrix.yaml")

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


def parse_permission_matrix(readable=True):
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
    def human_readable(data, headers):
        # display results in human readable format
        for user_type in data:
            print(user_type)
            print("| ".join([f"{header: <24}" for header in [""] + headers]))
            for model in data[user_type]:
                print(model)
                for field in data[user_type][model]:
                    print(f"- {field}")
                    for row in data[user_type][model][field]:
                        row[0] = "-- {}".format(row[0])
                        print("| ".join([f"{d: <24}" for d in row]))

    def machine_readable(data, states):
        # display results in machine readable format
        # d = {"user": {"status": {"model": {"field": {"perm": "value"}}}}}
        result = {}
        for user_type in data:
            result[user_type] = {}
            for state in states:
                result[user_type][state] = defaultdict(bool)
            for model in data[user_type]:
                for field, rows in data[user_type][model].items():
                    for row in rows:
                        permission_type = row.pop(0)
                        if field == "all":
                            key = (permission_type, "travel", model)
                        else:
                            key = (permission_type, model, field)
                        count = 0
                        for state in states:
                            if key not in result[user_type][state]:
                                result[user_type][state][key] = row[count]
                            else:
                                result[user_type][state][key] |= row[count]
                            count += 1

        pp = pprint.PrettyPrinter(indent=4)
        with open("travel_permissions.py", "w") as fp:
            fp.write("permissions = {}".format(
                pp.pformat(result).replace(
                    "defaultdict(<class 'bool'>,", ""
                ).replace(
                    "})", "}"
                )
            ))

    matrix = get_permission_matrix()
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

                    if field == "edit":
                        if matrix["travel"][user][status][model][field] is not False:
                            data[status][model_key]["all"][field] = True
                    elif field == "view":
                        if matrix["travel"][user][status][model][field] is not True:
                            data[status][model_key]["all"][field] = False
                    else:
                        if matrix["travel"][user][status][model][field]["edit"] is not False:
                            data[status][model_key][field]["edit"] = True
                        if matrix["travel"][user][status][model][field]["view"] is not True:
                            data[status][model_key][field]["view"] = False
        results[user] = data

    # transpose data
    data = {}
    headers = None
    for user_type in results:
        data[user_type] = {}
        if headers is None:
            headers = [k for k in results[user_type]]
        for header in results[user_type]:
            for model in results[user_type][header]:
                data[user_type][model] = defaultdict(list)
                for field in model_fields[model]:
                    for perm_type in ["edit", "view"]:
                        row = [perm_type]
                        for h in headers:
                            try:
                                row.append(results[user][h][model][field][perm_type])
                            except Exception:
                                row.append(False if perm_type == "edit" else True)
                        data[user_type][model][field].append(row)
            break

    if readable:
        human_readable(data, headers)
    else:
        machine_readable(data, headers)
