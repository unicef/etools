from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Permission


class HasTargetsPermission(BasePermission):
    """
    Permission for checking static targets list. This is usable for complex generic relations.
    """
    targets = []

    def get_targets(self, request, view):
        return self.targets

    def has_permission(self, request, view):
        targets = self.get_targets(request, view)
        context = view._collect_permission_context()

        permissions = Permission.objects.filter_by_context(context).filter_by_targets(targets)

        if request.method in SAFE_METHODS:
            permission_kind = Permission.PERMISSIONS.view
        else:
            permission_kind = Permission.PERMISSIONS.edit

        return bool(Permission.apply_permissions(permissions, targets, permission_kind))


def get_permission_for_targets(permission_targets):
    if isinstance(permission_targets, str):
        permission_targets = [permission_targets]

    class HasSpecificTargetsPermission(HasTargetsPermission):
        targets = permission_targets

    return HasSpecificTargetsPermission


class NestedPermission(HasTargetsPermission):
    """
    In case of nesting views we need to check access to child relation from parent instance.
    """

    def get_targets(self, request, view):
        model = view.get_queryset().model

        targets = []
        for lookup_field in view.parent_lookup_field.split('__'):
            field = getattr(model, lookup_field).field
            parent_model = field.related_model

            targets.append(Permission.get_target(parent_model, field.rel.get_accessor_name()))

            model = parent_model

        return targets
