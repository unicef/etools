from django.core.exceptions import ImproperlyConfigured
from rest_framework.decorators import action

from rest_framework.permissions import SAFE_METHODS, AllowAny

from unicef_restlib.views import NestedViewSetMixin

from etools.applications.permissions2.views import FSMTransitionActionMixin
from etools.applications.permissions_simplified.permissions import PermissionQ


class BaseSimplePermittedViewSetMixin(object):
    """
    Base class for simplified permissions.
    Check everything defined inside write_permission classes and set read_only attribute
    to serializer if write access restricted.
    Use same permissions as for permission_classes here.
    """

    write_permission_classes = []

    def get_write_permissions(self):
        return [permission() for permission in self.write_permission_classes]

    def check_write_permissions(self, instance=None, raise_error=True):
        write_permissions = self.get_write_permissions()

        read_only = not all(permission.has_permission(self.request, self) for permission in write_permissions)
        if instance and not read_only:
            read_only = not all(
                permission.has_object_permission(self.request, self, instance)
                for permission in write_permissions
            )

        if read_only and raise_error:
            self.permission_denied(self.request)

        return not read_only

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in SAFE_METHODS:
            self.check_write_permissions()

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method not in SAFE_METHODS:
            self.check_write_permissions(instance=obj)

    def get_serializer(self, instance=None, *args, **kwargs):
        many = kwargs.get('many')

        kwargs['read_only'] = not self.check_write_permissions(not many and instance, raise_error=False)
        serializer = super().get_serializer(instance=instance, *args, **kwargs)

        return serializer


class SimplePermittedParentViewSetMixin(object):
    """
    Check if write_permissions defined in root view.
    Else there is no sense to use permitted view.
    """

    def check_write_permissions(self, instance=None, raise_error=True):
        write_permissions = self.get_write_permissions()

        if getattr(self, 'parent', None) is None and not write_permissions:  # root view
            raise ImproperlyConfigured('write_permissions should be defined for root view.')

        return super().check_write_permissions(instance=instance, raise_error=raise_error)


class SimplePermittedChildViewSetMixin(NestedViewSetMixin):
    """
    Check write access to parent before checking self.
    """
    def check_parent_write_permissions(self, raise_error=True):
        parent_view = self.get_parent()
        if parent_view is None or not isinstance(parent_view, BaseSimplePermittedViewSetMixin):
            return True

        return parent_view.check_write_permissions(instance=self.get_parent_object(), raise_error=raise_error)

    def check_write_permissions(self, instance=None, raise_error=True):
        parent_write_allowed = self.check_parent_write_permissions(raise_error=raise_error)
        if not parent_write_allowed:
            if raise_error:
                self.permission_denied(self.request)
            else:
                return False

        return super().check_write_permissions(instance=instance, raise_error=raise_error)


class SimplePermittedViewSetMixin(SimplePermittedParentViewSetMixin, SimplePermittedChildViewSetMixin,
                                  BaseSimplePermittedViewSetMixin):
    """
    Combined class which can be used both for root & nested views.
    """
    pass


class SimplePermittedFSMTransitionActionMixin(FSMTransitionActionMixin):
    """
    Check if transition is allowed by its own list of permissions.
    Example:
    transition_permission_classes = {
        'complete': [UserIsPMEPermission],
        'cancel': [PermissionQ(UserIsPMEPermission) | PermissionQ(UserIsAuthorPermission)],
        'start': [write_permission_classes] # lists are allowed here
    }
    """
    transition_permission_classes = {}

    def get_transition_permissions(self, transition):
        return [
            permission() if not isinstance(permission, (list, set)) else PermissionQ(*permission)
            for permission in self.transition_permission_classes.get(transition, [])
        ]

    def pre_transition(self, instance, action):
        transition_permissions = self.get_transition_permissions(action)
        if not transition_permissions:
            self.permission_denied(self.request)

        allow_action = all(permission.has_permission(self.request, self) and
                           permission.has_object_permission(self.request, self, instance)
                           for permission in transition_permissions)

        if not allow_action:
            self.permission_denied(self.request)

        super().pre_transition(instance, action)


class SimplePermittedFSMViewSetMixin(SimplePermittedViewSetMixin, SimplePermittedFSMTransitionActionMixin):
    """
    When we use these two mixins together, we have implicit dependency of transition action
    from write_permission_classes, because get_object will check object permissions; POST will be recognised as
    unsafe method and write permissions will be checked. To fix this, we need to ignore them by overwriting
    property specifically for this action.
    """
    @action(detail=True, methods=['post'], url_path=r'(?P<action>\D+)', write_permission_classes=[AllowAny])
    def transition(self, request, *args, **kwargs):
        return super().transition(request, *args, **kwargs)
