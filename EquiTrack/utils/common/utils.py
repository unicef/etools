from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from itertools import chain

from django.contrib.contenttypes.fields import GenericForeignKey


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
