from rest_framework.permissions import BasePermission, SAFE_METHODS

from etools.applications.field_monitoring.groups import FMUser, PME


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
    def has_access(self, request, view, **kwargs):
        return request.method in SAFE_METHODS


IsEditAction = ~IsReadAction


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


class IsPersonResponsible(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return request.user == obj.person_responsible
