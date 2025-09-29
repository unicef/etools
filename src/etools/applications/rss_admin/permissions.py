from django.conf import settings

from rest_framework.permissions import BasePermission


class IsRssAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if not getattr(settings, 'RESTRICTED_ADMIN', True):
            return request.user.is_staff or request.user.is_superuser
        allowed = getattr(settings, 'ADMIN_EDIT_EMAILS', '')
        allowed_set = {email.strip().lower() for email in allowed.split(',') if email.strip()}
        return request.user.email and request.user.email.lower() in allowed_set
