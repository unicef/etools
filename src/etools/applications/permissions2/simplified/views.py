from django.core.exceptions import ImproperlyConfigured
from unicef_restlib.views import NestedViewSetMixin


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

        if instance:
            read_only = not all(permission.has_object_permission(self.request, self, instance)
                                for permission in write_permissions)

        else:
            read_only = not all(permission.has_permission(self.request, self)
                                for permission in write_permissions)

        if read_only and raise_error:
            self.permission_denied(self.request)

        return not read_only

    def get_serializer(self, instance=None, *args, **kwargs):
        many = kwargs.get('many')

        kwargs['read_only'] = not self.check_write_permissions(not many and instance, raise_error=False)
        serializer = super().get_serializer(instance=instance, *args, **kwargs)

        return serializer

    def perform_destroy(self, instance):
        self.check_write_permissions(instance=instance)

        super().perform_destroy(instance)


class SimplePermittedParentViewSetMixin(BaseSimplePermittedViewSetMixin):
    """
    Check if write_permissions defined in root view.
    Else there is no sense to use permitted view.
    """

    def check_write_permissions(self, instance=None, raise_error=True):
        write_permissions = self.get_write_permissions()

        if not hasattr(self, 'parent') and not write_permissions:
            raise ImproperlyConfigured('write_permissions should be defined for root view.')

        return super().check_write_permissions(instance=instance, raise_error=raise_error)


class SimplePermittedChildViewSetMixin(BaseSimplePermittedViewSetMixin, NestedViewSetMixin):
    """
    Check write access to parent before checking self.
    """
    def check_parent_write_permissions(self, raise_error=True):
        parent_view = self.get_parent()
        if not isinstance(parent_view, BaseSimplePermittedViewSetMixin):
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


class SimplePermittedViewSetMixin(SimplePermittedParentViewSetMixin, SimplePermittedChildViewSetMixin):
    """
    Combined class which can be used both for root & nested views.
    """
    pass
