from rest_framework.permissions import BasePermission

from etools.applications.eface.models import EFaceForm
from etools.applications.eface.validation.permissions import EFaceFormPermissions


def eface_form_field_is_editable_permission(field):
    """
    Check the user is able to edit selected eface form field.
    View should either implement get_root_object to return instance of EFaceForm (if view is nested),
    or return EFaceForm instance via get_object (can be used for detail actions).
    """

    class FieldPermission(BasePermission):
        def has_permission(self, request, view):
            if not view.kwargs:
                # This is needed for swagger to be able to build the correct structure
                # https://github.com/unicef/etools/pull/2540/files#r356446025
                return True

            if hasattr(view, 'get_root_object'):
                instance = view.get_root_object()
            else:
                instance = view.get_object()

            ps = EFaceForm.permission_structure()
            permissions = EFaceFormPermissions(
                user=request.user, instance=instance, permission_structure=ps
            )
            return permissions.get_permissions()['edit'].get(field)

        def has_object_permission(self, request, view, obj):
            return True

    return FieldPermission


class IsPartnerFocalPointPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.intervention.partner_focal_points.filter(email=request.user.email).exists()


class IsUNICEFFocalPointPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.intervention.unicef_focal_points.filter(email=request.user.email).exists()
