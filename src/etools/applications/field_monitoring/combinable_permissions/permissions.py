from django.core.exceptions import ImproperlyConfigured
from django.utils import tree

from rest_framework.permissions import BasePermission


# todo: move to the utils or something like that
class BaseQ(tree.Node):
    """
    Base class for logic nodes.

    BaseQ(first, second) - logic AND
    BaseQ(first) & BaseQ(second) - logic AND
    BaseQ(first) | BaseQ(second) - logic OR
    ~BaseQ(third) - logic NOT
    """
    # Connection types
    AND = 'AND'
    OR = 'OR'
    default = AND

    def __init__(self, *args, connector=None):
        super().__init__(children=list(args))
        self.connector = connector or self.default

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
        results = (getattr(child(), func_name)(*args, **kwargs) for child in self.children)

        if self.connector == self.AND:
            logic_result = all(results)
        elif self.connector == self.OR:
            logic_result = any(results)
        else:
            raise ImproperlyConfigured('Unknown connector {}'.format(self.connector))

        if self.negated:
            return not logic_result

        return logic_result

    def __call__(self):
        return self


class PermissionQ(BaseQ, BasePermission):
    """
    Encapsulates permissions as objects that can then be combined logically (using `&` and `|`).
    Call corresponding method for every child if being asked for permissions.
    """

    def has_permission(self, request, view):
        return self.execute('has_permission', request, view)

    def has_object_permission(self, request, view, obj):
        return self.execute('has_object_permission', request, view, obj)


class UserInGroup(BasePermission):
    """
    Allow access if user is in specific group.
    """
    group = None

    def has_permission(self, request, view):
        return self.group in map(lambda g: g.name, request.user.groups.all())
