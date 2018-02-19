import json

from django.core import serializers
from django.db import models
from django.utils import six


def model_instance_to_dictionary(obj):
    """
    Given a model instance `obj`, return a dictionary that represents it.
    E.g. something like
    {u'pk': 15, u'model': u'audit.auditorstaffmember', u'auditor_firm': 15, u'user': 934}

    For _simple_ use from templates, this'll work as well as the model instance itself.
    And it's trivially serializable by the default json encoder.
    That's all we really need here.
    """
    # We cannot just use model_to_dict, because it replaces instances with
    # their primary keys, and we want to replace them with dictionaries representing
    # each instance's fields' values.

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
