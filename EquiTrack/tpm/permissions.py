from __future__ import absolute_import, division, print_function, unicode_literals

from django.utils.translation import ugettext_lazy as _

from rest_framework.permissions import BasePermission, SAFE_METHODS

from tpm.models import PME


class IsPMEorReadonlyPermission(BasePermission):
    message = _('You have no power here')

    def has_permission(self, request, view):
        return (
            request.method in SAFE_METHODS or
            request.user and
            PME.as_group() in request.user.groups.all()
        )
