from rest_framework.permissions import IsAuthenticated

from etools.libraries.djangolib.utils import is_user_in_groups


class IsIPLMEditor(IsAuthenticated):

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.groups.filter(name='IP LM Editor').exists()


class LMSMAPIPermission(IsAuthenticated):

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return request.user.is_staff or is_user_in_groups(request.user, ['LMSMApi'])
