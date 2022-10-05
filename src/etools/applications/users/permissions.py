from django.conf import settings

from rest_framework.permissions import BasePermission

from etools.applications.organizations.models import Organization
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
                    organization=Organization.objects.get(vendor_number='UNICEF'),
                    group=PartnershipManager.as_group(),
                    is_active=True)\
            .exists()
