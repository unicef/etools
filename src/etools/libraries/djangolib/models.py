import weakref

from django.contrib.auth.models import Group
from django.db.models import Aggregate, CharField, Max, Value

from model_utils.managers import InheritanceManager


class GroupWrapper(object):
    """
    Wrapper for easy access to commonly used django groups and mapping shortcodes for them.
    example:

    UNICEFUser = GroupWrapper(code='unicef_user', name='UNICEF User')

    unicef_group = UNICEFUser.as_group() # group will be automatically created if not exists
    """

    code = None
    name = None
    _group = None
    _instances = []

    def __init__(self, code, name):
        self.__class__._instances.append(weakref.proxy(self))
        self.name = name
        self.code = code

    def __str__(self):
        return self.name

    def as_group(self):
        if not self._group:
            self._group, _ = Group.objects.get_or_create(name=self.name)
        return self._group

    def as_choice(self):
        return self.code, self.name

    def __eq__(self, other):
        if isinstance(other, Group):
            return other.name == self.name

        if isinstance(other, str):
            return other == self.code or other == self.name

        if self is other:
            return True

        return super() == other

    def invalidate_cache(self):
        self._group = None

    @classmethod
    def invalidate_instances(cls):
        for instance in cls._instances:
            instance.invalidate_cache()


class StringConcat(Aggregate):
    """ A custom aggregation function that returns "," separated strings """
    allow_distinct = True
    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, separator=",", distinct=False, **extra):
        super().__init__(
            expression,
            Value(separator),
            distinct='DISTINCT ' if distinct else '',
            output_field=CharField(),
            **extra
        )

    def as_postgresql(self, compiler, connection):
        self.function = 'STRING_AGG'
        return super().as_sql(compiler, connection)


class MaxDistinct(Max):
    allow_distinct = True


class DSum(Aggregate):
    function = 'SUM'
    template = '%(function)s(DISTINCT %(expressions)s)'
    name = 'Sum'


class InheritedModelMixin(object):
    """
    Mixin for easier access to subclasses. Designed to be tightly used with InheritanceManager
    """

    def get_subclass(self):
        if not self.pk:
            return self

        manager = self._meta.model._default_manager
        if not isinstance(manager, InheritanceManager):
            return self

        return manager.get_subclass(pk=self.pk)
