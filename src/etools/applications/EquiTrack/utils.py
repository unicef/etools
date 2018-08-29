"""
Project wide base classes and utility functions for apps
"""
import codecs
import csv
import json
from datetime import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db import connection
from django.db.models import Q

import requests


def get_environment():
    return settings.ENVIRONMENT


def get_current_site():
    return Site.objects.get_current()


def set_country(user, request):
    from etools.applications.users.models import Country

    country = request.GET.get(settings.SCHEMA_OVERRIDE_PARAM, None)
    if country:
        try:
            country = Country.objects.get(
                Q(name=country) |
                Q(country_short_code=country) |
                Q(schema_name=country)
            )
            if country in user.profile.countries_available.all():
                country = country
            else:
                country = None
        except Country.DoesNotExist:
            country = None

    request.tenant = country or user.profile.country or user.profile.country_override
    connection.set_tenant(request.tenant)


def get_data_from_insight(endpoint, data={}):
    url = '{}/{}'.format(
        settings.VISION_URL,
        endpoint
    ).format(**data)

    response = requests.get(
        url,
        headers={'Content-Type': 'application/json'},
        auth=(settings.VISION_USER, settings.VISION_PASSWORD),
        verify=False
    )
    if response.status_code != 200:
        return False, 'Loading data from Vision Failed, status {}'.format(response.status_code)
    try:
        result = json.loads(response.json())
    except ValueError:
        return False, 'Loading data from Vision Failed, no valid response returned for data: {}'.format(data)
    return True, result


class Vividict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


class HashableDict(dict):
    def __hash__(self):
        return hash(frozenset(self.items()))


def proccess_permissions(permission_dict):
    '''
    :param permission_dict: the csv file read as a generator of dictionaries
     where the header contains the following keys:

    'Group' - the Django Group the user should belong to - field may be blank.
    'Condition' - the condition that should be required to satisfy.
    'Status' - the status of the model (represents state)
    'Field' - the field we are targetting (eg: start_date) this needs to be spelled exactly as it is on the model
    'Action' - One of the following values: 'view', 'edit', 'required'
    'Allowed' - the boolean 'TRUE' or 'FALSE' if the action should be allowed if the: group match, status match and
    condition match are all valid

    *** note that in order for the system to know what the default behaviour should be on a specified field for a
    specific action, only the conditions opposite to the default should be defined.

    :return:
     a nested dictionary where the first key is the field targeted, the following nested key is the action possible,
     and the last nested key is the action parameter
     eg:
     {'start_date': {'edit': {'false': [{'condition': 'condition2',
                                         'group': 'UNICEF USER',
                                         'status': 'Active'}]},
                     'required': {'true': [{'condition': '',
                                            'group': 'UNICEF USER',
                                            'status': 'Active'},
                                           {'condition': '',
                                            'group': 'UNICEF USER',
                                            'status': 'Signed'}]},
                     'view': {'true': [{'condition': 'condition1',
                                        'group': 'PM',
                                        'status': 'Active'}]}}}
    '''

    result = Vividict()
    possible_actions = ['edit', 'required', 'view']

    for row in permission_dict:
        field = row['Field Name']
        action = row['Action'].lower()
        allowed = row['Allowed'].lower()
        assert action in possible_actions

        if isinstance(result[field][action][allowed], dict):
            result[field][action][allowed] = []

        # this action should not have been defined with any other allowed param
        assert list(result[field][action].keys()) == [allowed], \
            'There cannot be two types of "allowed" defined on the same ' \
            'field with the same action as the system will not be able' \
            ' to have a default behaviour.  field=%r, action=%r, allowed=%r' \
            % (field, action, allowed)

        result[field][action][allowed].append({
            'group': row['Group'],
            'condition': row['Condition'],
            'status': row['Status'].lower()
        })
    return result


def import_permissions(model_name):
    permission_file_map = {
        'Intervention': settings.PACKAGE_ROOT + '/assets/partner/intervention_permissions.csv',
        'Agreement': settings.PACKAGE_ROOT + '/assets/partner/agreement_permissions.csv'
    }

    def process_file():
        with codecs.open(permission_file_map[model_name], 'r', encoding='ascii') as csvfile:
            sheet = csv.DictReader(csvfile, delimiter=',', quotechar='|')
            result = proccess_permissions(sheet)
        return result

    cache_key = "public-{}-permissions".format(model_name.lower())
    response = cache.get_or_set(cache_key, process_file, 60 * 60 * 24)

    return response


def get_current_year():
    return datetime.today().year


def get_quarter(retrieve_date=None):
    if not retrieve_date:
        retrieve_date = datetime.today()
    month = retrieve_date.month
    if 0 < month <= 3:
        quarter = 'q1'
    elif 3 < month <= 6:
        quarter = 'q2'
    elif 6 < month <= 9:
        quarter = 'q3'
    else:
        quarter = 'q4'
    return quarter
