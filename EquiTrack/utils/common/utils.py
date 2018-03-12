from __future__ import absolute_import, division, print_function, unicode_literals

from collections import Iterable, Mapping
from itertools import chain

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import connection
from django.db.models import QuerySet, Manager
from django.utils import six

from rest_framework.fields import get_attribute

from users.models import Country


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


def pop_keys(d, keys):
    res, rem = dict(), dict()
    for key, value in d.items():
        if key in keys:
            res[key] = value
        else:
            rem[key] = value
    return res, rem


def run_on_all_tenants(function):
    with every_country() as c:
        for country in c:
            function()


class every_country:
    """
    Loop through every available available tenant/country, then revert back to whatever was set before.

    Example usage:

    with every_country() as c:
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


def get_attribute_smart(instance, attrs):
    """A bit smarter version of rest_framework.fields.get_attribute.
    Has ability to work with lists, so it can be used to look deep inside relations.
    Also is suitable for dicts.

    Example usage:

    get_attribute_smart({"instances": [{"id": 1}, {"id": 2}, {"id": 3}]}, "instances.id")
    """

    if instance is None or not attrs:
        return instance

    if isinstance(attrs, six.string_types):
        attrs = attrs.split('.')

    if isinstance(instance, (Iterable, QuerySet)) and not isinstance(instance, (Mapping, six.string_types)):
        instance = list([get_attribute_smart(obj, [attrs[0]]) for obj in instance])
        if all(map(lambda obj: isinstance(obj, QuerySet), instance)):
            instance = chain(*instance)
    else:
        instance = get_attribute(instance, [attrs[0]])

        if isinstance(instance, Manager):
            instance = instance.all()

    return get_attribute_smart(instance, attrs[1:])
