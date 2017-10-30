"""
Project wide base classes and utility functions for apps
"""
import csv
from functools import wraps
import json
import requests
import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.db import connection
from django.utils.cache import patch_cache_control
from rest_framework import status
from rest_framework.response import Response


def get_environment():
    return settings.ENVIRONMENT


def get_current_site():
    return Site.objects.get_current()


def get_changeform_link(model, link_name='View', action='change'):
    """
    Returns a html button to view the passed in model in the django admin
    """
    from .mixins import AdminURLMixin

    if model.id:
        url_name = AdminURLMixin.admin_url_name.format(
            app_label=model._meta.app_label,
            model_name=model._meta.model_name,
            action=action
        )
        changeform_url = reverse(url_name, args=(model.id,))
        return u'<a class="btn btn-primary default" ' \
               u'href="{}" target="_blank">{}</a>'.format(changeform_url, link_name)
    return u''


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


def load_internal_pdf_template(endpoint='', data={}):
    api_url = 'http://{}/{}/'.format(
        settings.PDF_API_URL,
        'api/pdf/' + endpoint
    )

    # return api_url
    response = requests.post(
        api_url,
        # data=data,
        json=data,
        headers={'Content-Type': 'application/json'},
        auth=(settings.PDF_API_USER, settings.PDF_API_PASSWORD),
        verify=False
    )

    return response


def etag_cached(cache_key, public_cache=False):
    """
    Returns list of instances only if there's a new ETag, and it does not
    match the one sent along with the request.
    Otherwise it returns 304 NOT MODIFIED.
    """
    assert isinstance(cache_key, (str, unicode)), 'Cache key has to be a string'

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
            result = proccess_permissions(sheet)
        return result

    cache_key = "public-{}-permissions".format(model_name.lower())
    # cache.delete(cache_key)
    response = cache.get_or_set(cache_key, process_file, 60*60*24)

    return response
