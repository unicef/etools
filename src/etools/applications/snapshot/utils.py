
from django.db.models.query import QuerySet
from django.forms import model_to_dict
from django.utils import six

from etools.applications.snapshot.models import Activity


def jsonify(data):
    """Convert data into a dictionary that can be json encoded"""
    allowed_types = six.integer_types + (
        six.text_type,
        bool,
        dict,
        float,
        list,
        set,
        tuple,
    )
    for key, value in data.items():
        if isinstance(value, QuerySet):
            data[key] = [v.pk for v in value]
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

    activity_kwargs = {
        'target': target,
        'by_user': by_user,
        'action': action,
        'data': current_obj_dict,
        'change': change
    }

    snapshot_additional_data = getattr(target, 'snapshot_additional_data', None)
    if callable(snapshot_additional_data):
        activity_kwargs['data'].update(snapshot_additional_data(change))

    activity = Activity.objects.create(**activity_kwargs)

    return activity
