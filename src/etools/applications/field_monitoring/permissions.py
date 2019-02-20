from rest_framework.permissions import BasePermission

from etools.applications.field_monitoring.groups import FMUser, PME
from etools.applications.permissions_simplified.permissions import UserInGroup


class IsFMUser(UserInGroup):
    group = FMUser.name


class IsPME(UserInGroup):
    group = PME.name


def visit_is(status):
    class VisitInStatus(BasePermission):
        def has_object_permission(self, request, view, obj):
            return obj.status == status

    return VisitInStatus


class UserIsDataCollector(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user in obj.team_members.all()


class UserIsPrimaryFieldMonitor(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.primary_field_monitor


UserIsFieldMonitor = IsFMUser | IsPME
