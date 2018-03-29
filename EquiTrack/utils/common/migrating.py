# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


def fix_null_values(model, field_names, new_value=''):
    """
    For each fieldname, update any records in 'model' where the field's value is NULL
    to be an empty string instead (or whatever new_value is)
    """
    for name in field_names:
        model._default_manager.filter(**{name: None}).update(**{name: new_value})
