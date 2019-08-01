from rest_framework.permissions import BasePermission, SAFE_METHODS

from etools.applications.field_monitoring.combinable_permissions.permissions import PermissionQ, UserInGroup
from etools.applications.field_monitoring.groups import FMUser, PME


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


class IsReadAction(SimplePermission):
    def has_access(self, request, view, **kwargs):
        return request.method in SAFE_METHODS


IsEditAction = ~PermissionQ(IsReadAction)


class IsObjectAction(SimplePermission):
    def has_access(self, request, view, instance=None):
        return (view.lookup_url_kwarg or view.lookup_field) in view.kwargs


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


class IsPersonResponsible(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return request.user == obj.person_responsible
