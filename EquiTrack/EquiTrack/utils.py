"""
Project wide base classes and utility functions for apps
"""
import datetime
from functools import wraps
from itertools import chain
import logging
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db import connection
from django.utils.cache import patch_cache_control

from rest_framework import status
from rest_framework.response import Response

from users.models import Country

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


def run_on_all_tenants(function):
    with EveryCountry() as c:
        for country in c:
            function()


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
