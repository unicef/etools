from rest_framework.permissions import BasePermission, SAFE_METHODS

from etools.applications.permissions2.models import Permission


class NestedPermission(BasePermission):
    """
    In case of nesting views we need to check access to child relation from parent instance.
    """

    def has_permission(self, request, view):
        parent_model = view.get_parent().get_queryset().model

        model = view.get_queryset().model
        field = getattr(model, view.parent_lookup_field).field

        target = Permission.get_target(parent_model, field.rel.get_accessor_name())

        context = view._collect_permission_context()

        permissions = Permission.objects.filter_by_context(context).filter_by_targets([target])

        if request.method in SAFE_METHODS:
            permission_kind = Permission.PERMISSIONS.view
        else:
            permission_kind = Permission.PERMISSIONS.edit

        return bool(Permission.apply_permissions(permissions, [target], permission_kind))
