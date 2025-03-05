from rest_framework.permissions import IsAuthenticated

from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.libraries.djangolib.utils import is_user_in_groups


class IsLMSMAdmin(IsAuthenticated):
    """
    Custom permission class to ensure the user:
      1. Is authenticated (via IsAuthenticated).
      2. Belongs to the 'IP LM Editor' group.
      3. Has at least one permission required for the requested view.
    """
    LMSM_ADMIN_GROUP = 'LMSM Admin Panel'

    MAPPED_VIEWS_TO_PERMS = {
        # Manage Users Perms
        USER_ADMIN_PANEL: [
            USER_ADMIN_PANEL_PERMISSION,
            USER_LOCATIONS_ADMIN_PANEL_PERMISSION,
            STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION,
        ],
        # Manage Locations Perms
        LOCATIONS_ADMIN_PANEL: [
            LOCATIONS_ADMIN_PANEL_PERMISSION,
            USER_LOCATIONS_ADMIN_PANEL_PERMISSION,
        ],
        LOCATIONS_TYPE_ADMIN_PANEL: [
            LOCATIONS_ADMIN_PANEL_PERMISSION,
        ],
        PARENT_LOCATIONS_ADMIN_PANEL: [
            LOCATIONS_ADMIN_PANEL_PERMISSION,
        ],
        # Manage Users linked to Locations Perms
        USER_LOCATIONS_ADMIN_PANEL: [
            USER_LOCATIONS_ADMIN_PANEL_PERMISSION,
        ],
        # Manage Email Alerts Perms
        ALERT_NOTIFICATIONS_ADMIN_PANEL: [
            ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION,
        ],
        ALERT_TYPES_ADMIN_PANEL: [
            ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION,
        ],
        # Manage Stock Management Perms
        STOCK_MANAGEMENT_ADMIN_PANEL: [
            STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION,
        ],
        STOCK_MANAGEMENT_MATERIALS_ADMIN_PANEL: [
            STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION,
        ],
        # Manage Transfer History Perms
        TRANSFER_HISTORY_ADMIN_PANEL: [
            TRANSFER_HISTORY_ADMIN_PANEL_PERMISSION,
        ],
        TRANSFER_EVIDENCE_ADMIN_PANEL: [
            TRANSFER_HISTORY_ADMIN_PANEL_PERMISSION,
        ],
    }

    def get_required_permissions(self, view_basename: str) -> set:
        return self.MAPPED_VIEWS_TO_PERMS.get(view_basename, set())

    def has_page_permission(self, request, view) -> bool:
        required_perms = self.get_required_permissions(view.basename)
        if not required_perms:
            return False
        required_perms = required_perms if request.method == 'GET' else required_perms[:1]
        return request.user.user_permissions.filter(
            codename__in=required_perms
        ).exists()

    def has_permission(self, request, view) -> bool:
        base_permission = super().has_permission(request, view)
        is_admin = request.user.groups.filter(name=self.LMSM_ADMIN_GROUP).exists()
        return base_permission and is_admin and self.has_page_permission(request, view)


class IsIPLMEditor(IsAuthenticated):

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.groups.filter(name='IP LM Editor').exists()


class LMSMAPIPermission(IsAuthenticated):

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request.user.is_staff or is_user_in_groups(request.user, ['LMSMApi'])
