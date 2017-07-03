"""
Project wide base classes and utility functions for apps
"""
import csv
import os
from collections import OrderedDict as SortedDict
from functools import wraps

import collections
from import_export.resources import ModelResource
import json
import requests
import tablib
import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import user_passes_test
from django.contrib.sites.models import Site
from django.contrib.staticfiles.templatetags.staticfiles import static
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


def get_staticfile_link(file_path):
    """
    Returns the full URL to a file in static files

    :param file_path: path to file relative to static files root
    :return: fully qualified URL to file
    """
    return static(file_path)


class BaseExportResource(ModelResource):

    headers = []

    def insert_column(self, row, field_name, value):
        """
        Inserts a column into a row with a given value
        or sets a default value of empty string if none
        """
        row[field_name] = value

    def insert_columns_inplace(self, row, fields, after_column):
        """
        Inserts fields with values into a row inplace
        and after a specific named column
        """
        keys = row.keys()
        before_column = None
        if after_column in row:
            index = keys.index(after_column)
            offset = index + 1
            if offset < len(row):
                before_column = keys[offset]

        for key, value in fields.items():
            if before_column:
                row.insert(offset, key, value)
                offset += 1
            else:
                row[key] = value

    def fill_row(self, resource, fields):
        """
        This performs the actual work of translating
        a model into a fields dictionary for exporting.
        Inheriting classes must implement this.
        """
        return NotImplementedError()

    def export(self, queryset=None):
        """
        Exports a resource.
        """

        #TODO quickly patched.. this whole code needs to be rewritten to for performance (streaming)



        if queryset is None:
            queryset = self.get_queryset()

        if getattr(self, 'up_queryset', None):
            queryset = self.up_queryset(queryset)


        fields = SortedDict()
        data = tablib.Dataset(headers=fields.keys())

        for model in queryset.iterator():
            # first pass creates table shape
            self.fill_row(model, fields)
            data.append(fields.keys())
            # run only once for the headers
            break

        self.headers = fields

        # Iterate without the queryset cache, to avoid wasting memory when
        # exporting large datasets.

        for model in queryset.all():
            # second pass creates rows from the known table shape
            row = fields.copy()
            self.fill_row(model, row)
            data.append(row.values())

        return data


def staff_test(u):
    if u.is_authenticated and u.email.endswith("unicef.org"):
        return True
    return False


def staff_required(function, home_url="/partners/", redirect_field_name=None):
    actual_decorator = user_passes_test(staff_test, home_url, redirect_field_name)
    return actual_decorator(function)


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
    except ValueError as e:
        return False, 'Loading data from Vision Failed, no valid response returned for data: {}'.format(data)
    return True, result


def etag_cached(cache_key, public_cache=False):
    """
    Returns list of instances only if there's a new ETag, and it does not
    match the one sent along with the request.
    Otherwise it returns 304 NOT MODIFIED.
    """
    assert isinstance(cache_key, (str, unicode)), 'Cache key has to be a string'

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if public_cache:
                schema_name = 'public'
            else:
                schema_name = connection.schema_name
            cache_etag = cache.get("{}-{}-etag".format(schema_name, cache_key))
            request_etag = self.request.META.get("HTTP_IF_NONE_MATCH", None)

            local_etag = cache_etag if cache_etag else '"{}"'.format(uuid.uuid4().hex)

            if cache_etag and request_etag and cache_etag == request_etag:
                response = Response(status=status.HTTP_304_NOT_MODIFIED)
            else:
                response = func(self, *args, **kwargs)
                response["ETag"] = local_etag

            if not cache_etag:
                cache.set("{}-locations-etag".format(schema_name), local_etag)

            patch_cache_control(response, private=True, must_revalidate=True)
            return response

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
        field = row['Field']
        action = row['action'].lower()
        allowed = row['allowed'].lower()
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
            'status': row['Status']
        })
    return result


def import_permissions(model_name):
    permission_file_map = {
        'Intervention': 'EquiTrack/assets/partner/intervention_permissions.csv'
    }
    def process_file():
        with open(permission_file_map[model_name], 'rb') as csvfile:
            sheet = csv.DictReader(csvfile, delimiter=',', quotechar='|')
            result = proccess_permissions(sheet)
        return result

    cache_key = "public-{}-permissions".format(model_name.lower())
    # cache.delete(cache_key)
    response = cache.get_or_set(cache_key, process_file(), 60*60*24)

    return response
