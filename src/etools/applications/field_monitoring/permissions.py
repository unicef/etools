from rest_framework.permissions import BasePermission, SAFE_METHODS

from etools.applications.field_monitoring.groups import FMUser, MonitoringVisitApprover
from etools.applications.field_monitoring.planning.activity_validation.permissions import ActivityPermissions
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.tpm.models import PME


class UserInGroup(BasePermission):
    """
    Allow access if user is in specific group.
    """
    group = None

    def has_permission(self, request, view):
        return self.group in map(lambda g: g.name, request.user.groups.all())


class SimplePermission(BasePermission):
    """
    Simple permission to prevent code duplication in has_permission & has_object_permission
    """
    def has_access(self, request, view, instance=None):
        raise NotImplementedError

    def has_permission(self, request, view):
        return self.has_access(request, view)

    def has_object_permission(self, request, view, obj):
        return self.has_access(request, view, instance=obj)

    class Meta:
        abstract = True


class IsReadAction(SimplePermission):
    def has_access(self, request, view, instance=None):
        return request.method in SAFE_METHODS


IsEditAction = ~IsReadAction


class IsParentAction(SimplePermission):
    def has_access(self, request, view, instance=None):
        return view.action == 'parent'


class IsObjectAction(SimplePermission):
    def has_access(self, request, view, instance=None):
        return (view.lookup_url_kwarg or view.lookup_field) in view.kwargs


IsListAction = ~IsObjectAction


class IsFMUser(UserInGroup):
    group = FMUser.name


class IsPME(UserInGroup):
    group = PME.name


class IsMonitoringVisitApprover(UserInGroup):
    group = MonitoringVisitApprover.name


IsFieldMonitor = IsFMUser | IsPME


class IsTeamMember(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return request.user in obj.team_members.all()


class IsActivityTeamMember(BasePermission):
    def has_permission(self, request, view):
        return request.user in view.get_root_object().team_members.all()

    def has_object_permission(self, request, view, obj):
        return True


class IsVisitLead(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return request.user == obj.visit_lead


def activity_field_is_editable_permission(field):
    """
    Check the user is able to edit selected monitoring activity field.
    View should either implement get_root_object to return instance of MonitoringActivity (if view is nested),
    or return MonitoringActivity instance via get_object (can be used for detail actions).
    """

    class FieldPermission(BasePermission):
        def has_permission(self, request, view):
            if not view.kwargs:
                # This is needed for swagger to be able to build the correct structure
                # https://github.com/unicef/etools/pull/2540/files#r356446025
                return True

            if hasattr(view, 'get_root_object'):
                instance = view.get_root_object()
            else:
                instance = view.get_object()

            ps = MonitoringActivity.permission_structure()
            permissions = ActivityPermissions(
                user=request.user, instance=instance, permission_structure=ps
            )
            return permissions.get_permissions()['edit'].get(field)

        def has_object_permission(self, request, view, obj):
            return True

    return FieldPermission
