from rest_framework.permissions import BasePermission, SAFE_METHODS

from etools.applications.field_monitoring.groups import FMUser, PME
from etools.applications.permissions_simplified.permissions import PermissionQ, UserInGroup


class IsReadAction(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS


IsEditAction = ~PermissionQ(IsReadAction)


class IsFMUser(UserInGroup):
    group = FMUser.name


class IsPME(UserInGroup):
    group = PME.name


def activity_is(status):
    class ActivityStatusPermission(BasePermission):
        def has_object_permission(self, request, view, obj):
            return obj.status == status

    return ActivityStatusPermission


class UserIsDataCollector(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user in obj.team_members.all()


class UserIsPersonResponsible(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.person_responsible


UserIsFieldMonitor = IsFMUser | IsPME
