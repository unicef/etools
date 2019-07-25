from rest_framework.permissions import BasePermission, SAFE_METHODS

from etools.applications.field_monitoring.groups import FMUser, PME
from etools.applications.field_monitoring.combinable_permissions.permissions import PermissionQ, UserInGroup


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


class IsFSMTransition(BasePermission):
    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return view.name == 'transition'


def transition_is(action):
    class TransitionPermission(BasePermission):
        def has_object_permission(self, request, view, obj):
            return self.kwargs.get('action') == action

    return TransitionPermission


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


IsFieldMonitor = IsFMUser | IsPME


class IsTeamMember(BasePermission):
    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return request.user in obj.team_members.all()
