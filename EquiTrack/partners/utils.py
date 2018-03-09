import csv
import datetime
import json

from django.conf import settings
from django.core.cache import cache
import requests


class Vividict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


class HashableDict(dict):
    def __hash__(self):
        return hash(frozenset(self.items()))


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


def process_permissions(permission_dict):
    '''
    :param permission_dict: the csv field read as a dictionary where the header contains the following keys:
    'Group' - the Django Group the user should belong to - field may be blank.
    'Condition' - the condition that should be required to satisfy.
    'Status' - the status of the model (represents state)
    'Field' - the field we are targetting (eg: start_date) this needs to be spelled exactly as it is on the model
    'Action' - One of the following values: 'view', 'edit', 'required'
    'Allowed' - the boolean 'TRUE' or 'FALSE' if the action should be allowed if the: group match, stastus match and
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
        assert result[field][action].keys() == [allowed], 'There cannot be two types of "allowed" defined on the same '\
                                                          'field with the same action as the system will not  be able' \
                                                          ' to have a default behaviour'

        result[field][action][allowed].append({
            'group': row['Group'],
            'condition': row['Condition'],
            'status': row['Status'].lower()
        })
    return result


def import_permissions(model_name):
    permission_file_map = {
        'Intervention': settings.SITE_ROOT + '/assets/partner/intervention_permissions.csv',
        'Agreement': settings.SITE_ROOT + '/assets/partner/agreement_permissions.csv'
    }

    def process_file():
        with open(permission_file_map[model_name], 'rb') as csvfile:
            sheet = csv.DictReader(csvfile, delimiter=',', quotechar='|')
            result = process_permissions(sheet)
        return result

    cache_key = "public-{}-permissions".format(model_name.lower())
    # cache.delete(cache_key)
    response = cache.get_or_set(cache_key, process_file, 60 * 60 * 24)

    return response


def get_quarter(retrieve_date=None):
    if not retrieve_date:
        retrieve_date = datetime.datetime.today()
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
