from __future__ import absolute_import, division, print_function, unicode_literals

from django.utils import six


def collect_parent_models(model):
    result = [model._meta.model_name, ]
    parent_models = model._meta.get_parent_list()
    for parent in parent_models:
        result += collect_parent_models(parent)
    return result


def has_action_permission(permission_class, instance=None, user=None, action=None):
    if instance and user and action:
        return permission_class.objects.filter(
            user=user, permission=permission_class.PERMISSIONS.action, target__in=map(
                lambda related_model: related_model + '.' + action, collect_parent_models(instance._meta.model)
            ), instance=instance).exists()

    if action and not instance and not user:
        return lambda instance, user: has_action_permission(instance, user, action)

    if action and instance:
        return lambda user: has_action_permission(instance, user, action)

    assert False


def is_user_in_groups(user, group_names):
    '''Utility function; returns True if user is in ANY of the groups in the group_names list, False if the user
    is in none of them. Note that group_names should be a tuple or list, not a single string.
    '''
    if isinstance(group_names, six.string_types):
        # Anticipate common programming oversight.
        raise ValueError('group_names parameter must be a tuple or list, not a string')
    return user.groups.filter(name__in=group_names).exists()
