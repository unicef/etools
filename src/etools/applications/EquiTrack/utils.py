"""
Generic classes/functions that don't fit anywhere specifically
and not enough to make into a library

Used throughout the eTools project
"""
import datetime
import json
import uuid

from functools import wraps
from itertools import chain
import logging

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.sites.models import Site
from django.core import serializers
from django.core.cache import cache
from django.db import connection, models
from django.utils import six
from django.utils.cache import patch_cache_control

from rest_framework import status
from rest_framework.response import Response

from etools.applications.users.models import Country

logger = logging.getLogger(__name__)


def get_environment():
    return settings.ENVIRONMENT


def get_current_site():
    return Site.objects.get_current()


class EveryCountry:
    """
    Loop through every available available tenant/country, then revert back to whatever was set before.

    Example usage:

    with EveryCountry() as c:
        for country in c:
            print(country.name)
            function()
    """
    original_country = None

    def __enter__(self):
        self.original_country = connection.tenant
        for c in Country.objects.exclude(name='Global').all():
            connection.set_tenant(c)
            yield c

    def __exit__(self, type, value, traceback):
        connection.set_tenant(self.original_country)


def run_on_all_tenants(function, **kwargs):
    with EveryCountry() as c:
        for country in c:
            function(**kwargs)


def set_country(user, request):
    request.tenant = user.profile.country or user.profile.country_override
    connection.set_tenant(request.tenant)


def set_country_by_name(name):
    connection.set_tenant(Country.objects.get(name=name))
    logger.info(u'Set in {} workspace'.format(name))


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


def get_current_year():
    return datetime.date.today().year


def get_all_field_names(TheModel):
    '''Return a list of all field names that are possible for this model (including reverse relation names).
    Any internal-only field names are not included.

    Replacement for MyModel._meta.get_all_field_names() which does not exist under Django 1.10.
    https://github.com/django/django/blob/stable/1.7.x/django/db/models/options.py#L422
    https://docs.djangoproject.com/en/1.10/ref/models/meta/#migrating-from-the-old-api
    '''
    return list(set(chain.from_iterable(
        (field.name, field.attname) if hasattr(field, 'attname') else (field.name,)
        for field in TheModel._meta.get_fields()
        if not (field.many_to_one and field.related_model is None) and
        not isinstance(field, GenericForeignKey)
    )))


def strip_text(text):
    return '\r\n'.join(map(lambda line: line.lstrip(), text.splitlines()))


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


def fix_null_values(model, field_names, new_value=''):
    """
    For each fieldname, update any records in 'model' where the field's value is NULL
    to be an empty string instead (or whatever new_value is)
    """
    for name in field_names:
        model._default_manager.filter(**{name: None}).update(**{name: new_value})
