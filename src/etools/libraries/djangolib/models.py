import weakref
from datetime import datetime

from django.contrib.auth.models import Group
from django.db import models
from django.db.models import Aggregate
from django.db.models.manager import BaseManager
from django.db.models.query import QuerySet
from django.utils.timezone import now

from model_utils.managers import InheritanceManager
from pytz import UTC

# UTC have to be here to be able to directly compare with the values from the db (orm always returns tz aware values)
EPOCH_ZERO = datetime(1970, 1, 1, tzinfo=UTC)


class GroupWrapper:
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


class StringConcat(models.Aggregate):
    """ A custom aggregation function that returns "," separated strings """
    allow_distinct = True
    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, separator=",", distinct=False, **extra):
        super().__init__(
            expression,
            models.Value(separator),
            distinct='DISTINCT ' if distinct else '',
            output_field=models.CharField(),
            **extra
        )

    def as_postgresql(self, compiler, connection):
        self.function = 'STRING_AGG'
        return super().as_sql(compiler, connection)


class MaxDistinct(models.Max):
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


class ValidityQuerySet(QuerySet):
    def delete(self):
        self.update(deleted_at=now())


class ValidityManager(BaseManager.from_queryset(ValidityQuerySet)):
    """
    Manager which overwrites the delete method to support soft delete functionality
    By default it filters out all soft deleted instances
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at=EPOCH_ZERO)


class SoftDeleteMixin(models.Model):
    """
    This is a mixin to support soft deletion for specific models. This behavior is required to keep everything in the
    database but still hide it from the end users. Example: Country changes currency - the old one has to be kept but
    hidden (soft deleted)

    The functionality achieved by using the SoftDeleteMixin and the ValidityManager. Both of them are depending on the
    `deleted_at` field, which defaults to EPOCH_ZERO to allow unique constrains in the db.
    IMPORTANT: Default has to be a value - boolean field or nullable datetime would not work
    IMPORTANT #2: This model does not prevent cascaded deletion - this can only happen if the soft deleted model points
                  to one which actually deletes the entity from the database
    """

    deleted_at = models.DateTimeField(default=EPOCH_ZERO, verbose_name='Deleted At')

    # IMPORTANT: The order of these two queryset is important. The normal queryset has to be defined first to have that
    #            as a default queryset
    admin_objects = QuerySet.as_manager()
    objects = ValidityManager()

    class Meta:
        abstract = True

    def force_delete(self, using=None, keep_parents=False):
        return super().delete(using, keep_parents)

    def delete(self, *args, **kwargs):
        self.deleted_at = now()
        self.save()
