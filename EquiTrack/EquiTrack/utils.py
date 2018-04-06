"""
Project wide base classes and utility functions for apps
"""
import codecs
import csv
import json
import uuid
from functools import wraps

from datetime import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import serializers
from django.core.cache import cache
from django.db import connection, models
from django.utils import six
from django.utils.cache import patch_cache_control

import requests
from rest_framework import status
from rest_framework.response import Response


def get_environment():
    return settings.ENVIRONMENT


def get_current_site():
    return Site.objects.get_current()


def set_country(user, request):

    request.tenant = user.profile.country or user.profile.country_override
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


def etag_cached(cache_key, public_cache=False):
    """
    Returns list of instances only if there's a new ETag, and it does not
    match the one sent along with the request.
    Otherwise it returns 304 NOT MODIFIED.
    """
    assert isinstance(cache_key, six.string_types), 'Cache key has to be a string'

    def make_cache_key():
        if public_cache:
            schema_name = 'public'
        else:
            schema_name = connection.schema_name

        return '{}-{}-etag'.format(schema_name, cache_key)

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):

            cache_etag = cache.get(make_cache_key())
            request_etag = self.request.META.get("HTTP_IF_NONE_MATCH", None)

            local_etag = cache_etag if cache_etag else '"{}"'.format(uuid.uuid4().hex)

            if cache_etag and request_etag and cache_etag == request_etag:
                response = Response(status=status.HTTP_304_NOT_MODIFIED)
            else:
                response = func(self, *args, **kwargs)
                response["ETag"] = local_etag

            if not cache_etag:
                cache.set(make_cache_key(), local_etag)

            patch_cache_control(response, private=True, must_revalidate=True)
            return response

        def invalidate():
            cache.delete(make_cache_key())

        wrapper.invalidate = invalidate
        return wrapper
    return decorator


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
        'Intervention': settings.SITE_ROOT + '/assets/partner/intervention_permissions.csv',
        'Agreement': settings.SITE_ROOT + '/assets/partner/agreement_permissions.csv'
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


def model_instance_to_dictionary(obj):
    """
    Given a model instance `obj`, return a dictionary that represents it.
    E.g. something like
    {u'pk': 15, u'model': u'audit.auditorstaffmember', u'auditor_firm': 15, u'user': 934}

    For _simple_ use from templates, this'll work as well as the model instance itself.
    And it's trivially serializable by the default json encoder.
    That's all we really need here.
    """
    # We cannot just use model_to_dict, because it excludes non-editable fields
    # unconditionally, and we want them all.

    # Note that Django's serializers only work on iterables of model instances

    json_string = serializers.serialize('json', [obj])
    # The string will deserialize to a list with one simple dictionary, like
    #  {u'pk': 15, u'model': u'audit.auditorstaffmember', u'fields': {u'auditor_firm': 15, u'user': 934}}
    d = json.loads(json_string)[0]
    # Promote the fields into the main dictionary
    d.update(**d.pop('fields'))
    return d


def make_dictionary_serializable(data):
    """
    Return a new dictionary, which is a copy of data, but
    if data is a dictionary with some model instances as values,
    the model instances are replaced with dictionaries so that
    the whole thing should be serializable.
    """
    return {
        k: model_instance_to_dictionary(v) if isinstance(v, models.Model) else v
        for k, v in six.iteritems(data)
    }
