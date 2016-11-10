from rest_framework import permissions


class PartnerPermission(permissions.BasePermission):
    message = 'Accessing this Intervention is not allowed.'

    def _has_access_permissions(self, user, object):
        if user.is_staff or \
                user.profile.partner_staff_member in \
                object.partner.partnerstaffmember_set.values_list('id', flat=True):
            return True

    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj)


class PartnerManagerPermission(permissions.BasePermission):
    message = 'Accessing this Intervention is not allowed.'

    def has_permission(self, request, view):
        if request.user.profile.partner_staff_member:
            return True
        if request.user.is_staff and request.method in permissions.SAFE_METHODS:
            return True

    def has_object_permission(self, request, view, obj):
        if request.user.profile.partner_staff_member in \
                obj.partner.partnerstaffmember_set.values_list('id', flat=True):
            return True
        if request.user.is_staff and request.method in permissions.SAFE_METHODS:
            return True


class ResultChainPermission(permissions.BasePermission):
    message = 'Accessing this ResultChain is not allowed.'

    def _has_access_permissions(self, user, result_chain):
        if user.is_staff or \
                user.profile.partner_staff_member in \
                result_chain.partnership.partner.partnerstaffmember_set.values_list('id', flat=True):
            return True

    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            # Check permissions for read-only request
            return self._has_access_permissions(request.user, obj)
        else:
            # Check permissions for write request
            return self._has_access_permissions(request.user, obj)
