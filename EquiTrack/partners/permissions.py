from rest_framework import permissions


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
