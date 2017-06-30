from rest_framework import permissions
from django.utils.lru_cache import lru_cache

class HDict(dict):
    def __hash__(self):
        return hash(frozenset(self.items()))

class InterventionPermissions(object):

    def condition_group_valid(self, condition_group):
        if self.intervention.status == condition_group['status'] and \
                        condition_group['group'] in self.user_groups and \
                self.condition_map[condition_group['condition']]:
            return True
        return False

    def __init__(self, user, intervention, permission_structure):
        self.user = user
        self.user_groups = self.user.groups.values_list('name', flat=True)
        self.intervention = intervention
        self.permission_structure = permission_structure
        self.condition_map = {
            'condition1': self.user in self.intervention.unicef_focal_points.all(),
            'condition2': self.user in self.intervention.partner_focal_points.all()
        }
        self.condition_group_valid = lru_cache(maxsize=16)(self.condition_group_valid)


    def get_field_permissions(self, action, field):
        condition_groups = field[action]
        for condition_group in condition_groups:
            if self.condition_group_valid(HDict(condition_group)):
                return True
        return False

    def get_permissions(self):
        ps = self.permission_structure
        actions = ['edit', 'required']
        my_permissions = {}
        for action in actions:
            my_permissions[action] = {}
            for field in ps:
                print field
                my_permissions[action][field] = self.get_field_permissions(action, ps[field])
        return my_permissions


class PartnerPermission(permissions.BasePermission):
    message = 'Accessing this Intervention is not allowed.'

    def _has_access_permissions(self, user, object):
        if user.is_staff or \
                user.profile.partner_staff_member in \
                object.partner.staff_members.values_list('id', flat=True):
            return True

    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj)


class PartneshipManagerPermission(permissions.BasePermission):
    message = 'Accessing this item is not allowed.'

    def _has_access_permissions(self, user, object):
        if user.is_staff or \
                user.profile.partner_staff_member in \
                object.partner.staff_members.values_list('id', flat=True):
            return True

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            # Check permissions for read-only request
            return request.user.is_staff
        else:
            return request.user.groups.filter(name='Partnership Manager').exists()

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj) and \
                request.user.groups.filter(name='Partnership Manager').exists()


class PartneshipManagerRepPermission(permissions.BasePermission):
    message = 'Accessing this item is not allowed.'

    def _has_access_permissions(self, user, object):
        if user.is_staff or \
                user.profile.partner_staff_member in \
                object.partner.staff_members.values_list('id', flat=True):
            return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj) and \
                request.user.groups.filter(name__in=['Partnership Manager', 'Senior Management Team',
                                                     'Representative Office']).exists()


class ResultChainPermission(permissions.BasePermission):
    message = 'Accessing this ResultChain is not allowed.'

    def _has_access_permissions(self, user, result_chain):
        if user.is_staff or \
                user.profile.partner_staff_member in \
                result_chain.partnership.partner.staff_members.values_list('id', flat=True):
            return True

    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj)
