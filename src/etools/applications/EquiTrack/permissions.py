from rest_framework.permissions import BasePermission


class IsSuperUserOrStaff(BasePermission):
    """
    Allows access to super users or staff.
    """

    def has_permission(self, request, view):
        return request.user and (request.user.is_superuser or request.user.is_staff)
