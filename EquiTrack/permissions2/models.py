from __future__ import unicode_literals

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import six

from model_utils import Choices


class PermissionQuerySet(models.QuerySet):
    def filter_by_context(self, context):
        return self.filter(condition__contained_by=context)


@six.python_2_unicode_compatible
class Permission(models.Model):
    PERMISSIONS = Choices(
        ('view', 'View'),
        ('edit', 'Edit'),
        ('action', 'Action'),
    )

    TYPES = Choices(
        ('allow', 'Allow'),
        ('disallow', 'Disallow'),
    )

    permission = models.CharField(max_length=10, choices=PERMISSIONS)
    permission_type = models.CharField(max_length=10, choices=TYPES, default=TYPES.allow)
    target = models.CharField(max_length=100)
    condition = ArrayField(models.CharField(max_length=100), default=[], blank=True)

    objects = PermissionQuerySet.as_manager()

    def __str__(self):
        return '{} permission to {} {} at {}'.format(
            self.permission_type.title(),
            self.permission,
            self.target,
            self.condition,
        )
