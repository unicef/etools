from .models import BasePermission, StatusBasePermission


def prepare_permission_choices(models):
    for model in models:
        if isinstance(model, BasePermission):
            model._meta.get_field('user_type').choices = model.USER_TYPES
        if isinstance(model, StatusBasePermission):
            model._meta.get_field('instance_status').choices = model.STATUSES
