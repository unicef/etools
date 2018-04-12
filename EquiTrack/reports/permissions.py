from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework import permissions

from utils.permissions.utils import is_user_in_groups


class PMEPermission(permissions.BasePermission):
    '''Applies general and object-based permissions.

    - For create views --
      - user must be in 'PME' group

    - For update/delete views --
      - user must be 'PME' group
    '''
    message = 'Accessing this item is not allowed.'

    def _has_write_permissions(self, user):
        '''True if --
              - user is 'PME' group member
        '''
        return is_user_in_groups(user, ['PME'])

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            return self._has_write_permissions(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            return self._has_write_permissions(request.user)
