from django.conf import settings

from rest_framework.permissions import BasePermission

from etools.applications.users.models import PartnershipManager


class IsServiceNowUser(BasePermission):
    """Allows access only to super users."""

    def has_permission(self, request, view):
        return request.user and request.user.username == settings.SERVICE_NOW_USER


class IsPartnershipManager(BasePermission):
    """Allows access only to PartnershipManager."""

    def has_permission(self, request, view):
        return request.user.realms\
            .filter(country=request.user.profile.country,
                    organization=request.user.profile.organization,
                    group=PartnershipManager.as_group())\
            .exists()


class IsActiveInRealm(BasePermission):
    """Allows access to users who are in the current realm, despite of their groups"""

    def has_permission(self, request, view):
        return request.user.realms \
            .filter(country=request.user.profile.country,
                    organization=request.user.profile.organization) \
            .exists()
