from django.core.exceptions import ImproperlyConfigured
from django.utils import tree

from rest_framework.permissions import BasePermission


class BaseQ(tree.Node):
    """
    Encapsulates permissions as objects that can then be combined logically (using `&` and `|`).
    """
    # Connection types
    AND = 'AND'
    OR = 'OR'
    default = AND

    def __init__(self, *args):
        super().__init__(children=list(args))
        self.connector = self.default

    def _combine(self, other, conn):
        if not isinstance(other, BaseQ):
            raise TypeError(other)
        obj = type(self)()
        obj.connector = conn
        obj.add(self, conn)
        obj.add(other, conn)
        return obj

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __and__(self, other):
        return self._combine(other, self.AND)

    def __invert__(self):
        obj = type(self)()
        obj.add(self, self.AND)
        obj.negate()
        return obj

    def execute(self, func_name, *args, **kwargs):
        results = (getattr(child, func_name)(*args, **kwargs) for child in self.children)

        if self.connector == self.AND:
            return all(results)
        elif self.connector == self.OR:
            return any(results)
        else:
            raise ImproperlyConfigured('Unknown connector {}'.format(self.connector))

    def __call__(self):
        return self


class PermissionQ(BaseQ, BasePermission):
    def has_permission(self, request, view):
        return self.execute('has_permission', request, view)

    def has_object_permission(self, request, view, obj):
        return self.execute('has_object_permission', request, view, obj)


class SimpleCommonPermission(BasePermission):
    """This permissions is unrelated from obj, so no need to make special logic related to object."""

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class UserInGroup(SimpleCommonPermission):
    group = None

    def has_permission(self, request, view):
        return self.group in map(lambda g: g.name, request.user.groups.all())
