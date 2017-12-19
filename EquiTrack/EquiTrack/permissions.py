from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """
    Allows access only to super users.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class IsSuperUserOrStaff(BasePermission):
    """
    Allows access to super users or staff.
    """

    def has_permission(self, request, view):
        return request.user and (request.user.is_superuser or request.user.is_staff)
