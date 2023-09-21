from django.conf import settings

from rest_framework.permissions import BasePermission


class IsServiceNowUser(BasePermission):
    """Allows access only to super users."""

    def has_permission(self, request, view):
        return request.user and request.user.username == settings.SERVICE_NOW_USER


class IsActiveInRealm(BasePermission):
    """Allows access to users who are in the current realm, despite their groups"""

    def has_permission(self, request, view):
        return request.user.groups.exists()
