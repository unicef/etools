from __future__ import unicode_literals

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import six

from model_utils import Choices

from .conditions import BaseCondition


class PermissionQuerySet(models.QuerySet):
    def filter_by_context(self, context):
        for i in range(len(context)):
            if isinstance(context[i], BaseCondition):
                context[i] = context[i].to_internal_value()

        return self.filter(condition__contained_by=context)

    def filter_by_targets(self, targets):
        wildcards = list(set(map(lambda target: target.rsplit('.', 1)[0] + '.*', targets)))
        targets = targets + wildcards

        return self.filter(target__in=targets)


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

    @staticmethod
    def get_target(model, field):
        if hasattr(field, 'name'):
            field = field.name
        elif hasattr(field, 'field_name'):
            field = field.field_name

        return '{}_{}.{}'.format(model._meta.app_label, model._meta.model_name, field)

    @classmethod
    def apply_permissions(cls, permissions, targets, kind):
        permissions = list(permissions)
        permissions.sort(key=lambda perm: (-len(perm.condition), '*' in perm.target))

        allowed_targets = []
        targets = set(targets)
        for perm in permissions:
            if kind == cls.PERMISSIONS.view:
                # If you can edit field you can view it too.
                if perm.permission not in [cls.PERMISSIONS.view, cls.PERMISSIONS.edit]:
                    continue
            elif perm.permission != kind:
                continue

            if perm.target[-1] == '*':
                affected_targets = set(filter(lambda target: target.startswith(perm.target[:-1]), targets))
            else:
                affected_targets = {perm.target}

            if not affected_targets:
                continue

            if perm.permission_type == cls.TYPES.allow and affected_targets & targets:
                allowed_targets.extend(affected_targets)

            targets -= affected_targets

        return allowed_targets
