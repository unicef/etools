from __future__ import absolute_import, division, print_function, unicode_literals

from collections import Iterable, Mapping
from itertools import chain

from django.db.models import QuerySet, Manager
from django.utils import six

from rest_framework.fields import get_attribute


def pop_keys(d, keys):
    res, rem = dict(), dict()
    for key, value in d.items():
        if key in keys:
            res[key] = value
        else:
            rem[key] = value
    return res, rem


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
