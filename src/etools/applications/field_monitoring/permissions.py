from rest_framework.permissions import BasePermission, SAFE_METHODS

from etools.applications.field_monitoring.groups import FMUser, PME
from etools.applications.field_monitoring.planning.activity_validation.permissions import ActivityPermissions
from etools.applications.field_monitoring.planning.models import MonitoringActivity


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
        return view.detail


IsListAction = ~IsObjectAction


class IsFMUser(UserInGroup):
    group = FMUser.name


class IsPME(UserInGroup):
    group = PME.name


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


class IsPersonResponsible(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return request.user == obj.person_responsible


class IsActivityPersonResponsible(BasePermission):
    def has_permission(self, request, view):
        return request.user == view.get_root_object().person_responsible

    def has_object_permission(self, request, view, obj):
        return True


def activity_field_is_editable_permission(field):
    class FieldPermission(BasePermission):
        def has_permission(self, request, view):
            if not view.kwargs:
                return True

            ps = MonitoringActivity.permission_structure()
            permissions = ActivityPermissions(
                user=request.user, instance=view.get_root_object(), permission_structure=ps
            )
            return permissions.get_permissions()['edit'].get(field)

        def has_object_permission(self, request, view, obj):
            return True

    return FieldPermission
