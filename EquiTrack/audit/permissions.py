from __future__ import absolute_import, division, print_function, unicode_literals

from django.utils.translation import ugettext_lazy as _
from rest_framework import permissions

from audit.models import UNICEFAuditFocalPoint, Auditor


# todo: remove
class CanCreateStaffMembers(permissions.BasePermission):
    message = _('User is not UNICEF audit focal point')

    def is_focal_point(self, request, view):
        return request.user.groups.filter(
            id=UNICEFAuditFocalPoint.as_group().id
        ).exists()

    def is_auditor(self, request, view):
        if not request.user.groups.filter(id=Auditor.as_group().id).exists():
            return False

        audit_organization = view.get_parent_object()
        return audit_organization.staff_members.filter(user_id=request.user.id).exists()

    def has_permission(self, request, view):
        return self.is_focal_point(request, view) or self.is_auditor(request, view)
