from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.forms import model_to_dict

from snapshot.models import Activity
from django.utils import six


def jsonify(data):
    """Convert data into a dictionary that can be json encoded"""
    allowed_types = (
        six.string_types,
        bool,
        dict,
        float,
        int,
        int,
        list,
        set,
        tuple,
    )
    for key, value in data.items():
        if not isinstance(value, allowed_types):
            data[key] = six.text_type(data[key])
    return data


def get_to_many_field_names(cls):
    """Get all the many_to_many and one_to_many field names for a class"""
    fields = []
    for field in cls._meta.get_fields():
        if field.one_to_many or field.many_to_many:
            fields.append(field.name)
    return fields


def create_dict_with_relations(obj):
    """Convert obj instance to a dictionary and then set
    many_to_many and one_to_many relation values, using their pk values

    These relations do not show up initially in the conversion of object
    to a dictionary format.
    """
    obj_dict = {}
    if obj is not None:
        # re-query obj to by-pass any caching (prefetch_related)
        obj = obj.__class__.objects.get(pk=obj.pk)
        obj_dict = jsonify(model_to_dict(obj))
        fields = get_to_many_field_names(obj)
        for field_name in fields:
            if hasattr(obj, field_name):
                field = getattr(obj, field_name)
                obj_dict[field_name] = [x.pk for x in field.all()]

    return obj_dict


def create_change_dict(prev_dict, current_dict):
    """Create a dictionary showing the differences between the
    initial target and the target after being saved.

    If prev_dict is empty, then change is empty as well
    """
    change = {}
    if prev_dict is not None:
        for k, v in prev_dict.items():
            if k in current_dict and current_dict[k] != prev_dict[k]:
                change.update({
                    k: jsonify({
                        "before": prev_dict[k],
                        "after": current_dict[k],
                    })
                })

    return change


def create_snapshot(target, target_before, by_user):
    """If target_before is empty, then action is create, otherwise update

    Create a dictionary of change between target before save and after.
    """
    action = Activity.UPDATE if target_before else Activity.CREATE
    current_obj_dict = create_dict_with_relations(target)
    change = create_change_dict(target_before, current_obj_dict)

    activity = Activity.objects.create(
        target=target,
        by_user=by_user,
        action=action,
        data=current_obj_dict,
        change=change
    )

    return activity
