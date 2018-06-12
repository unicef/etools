from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Permission


class NestedPermission(BasePermission):
    """
    In case of nesting views we need to check access to child relation from parent instance.
    """

    def has_permission(self, request, view):
        model = view.get_queryset().model

        targets = []
        for lookup_field in view.parent_lookup_field.split('__'):
            field = getattr(model, lookup_field).field
            parent_model = field.related_model

            targets.append(Permission.get_target(parent_model, field.rel.get_accessor_name()))

            model = parent_model

        context = view._collect_permission_context()

        permissions = Permission.objects.filter_by_context(context).filter_by_targets(targets)

        if request.method in SAFE_METHODS:
            permission_kind = Permission.PERMISSIONS.view
        else:
            permission_kind = Permission.PERMISSIONS.edit

        return bool(Permission.apply_permissions(permissions, targets, permission_kind))
