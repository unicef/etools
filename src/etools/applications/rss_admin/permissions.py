from django.conf import settings
from django.db import connection

from rest_framework.permissions import BasePermission


class IsRssAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # allow staff/superuser as fallback for local/dev if restriction disabled
        if not getattr(settings, 'RESTRICTED_ADMIN', True):
            return request.user.is_staff or request.user.is_superuser

        return request.user.realms.filter(
            country=connection.tenant,
            is_active=True,
            group__name__iexact='Rss Admin'
        ).exists()
