from django.utils.translation import ugettext_lazy as _

from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import PME


class IsPMEorReadonlyPermission(BasePermission):
    def has_permission(self, request, view):
        return (
            request.method in SAFE_METHODS or
            request.user and
            PME.as_group() in request.user.groups.all()
        )


class CanCreateStaffMembers(BasePermission):
    message = _('User is not PME')

    def has_permission(self, request, view):
        return request.user.groups.filter(
            id=PME.as_group().id
        ).exists()
