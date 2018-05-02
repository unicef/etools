from django.apps import apps
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import six

from model_utils import Choices

from .conditions import BaseCondition
from .utils import collect_child_models, collect_parent_models


class PermissionQuerySet(models.QuerySet):
    def filter_by_context(self, context):
        context = list(context)
        i = 0
        while i < len(context):
            if isinstance(context[i], BaseCondition):
                context[i] = context[i].to_internal_value()

            if isinstance(context[i], (list, tuple)):
                context.extend(context[i])
                context.pop(i)
            else:
                i += 1

        return self.filter(condition__contained_by=context)

    def filter_by_targets(self, targets):
        targets = list(targets)

        i = 0
        parent_map = dict()
        while i < len(targets):
            target = targets[i]

            model, field_name = Permission.parse_target(target)
            if model in parent_map:
                parents = parent_map[model]
            else:
                parents = collect_parent_models(model, levels=1)
                parent_map[model] = parents

            targets.extend([Permission.get_target(parent, field_name) for parent in parents])

            i += 1

        wildcards = list(set(map(lambda target: target.rsplit('.', 1)[0] + '.*', targets)))
        targets = targets + wildcards

        return self.filter(target__in=targets)


@six.python_2_unicode_compatible
class Permission(models.Model):
    """
    Model describes field-level permissions.
    Main idea is to provide different set of readable/writable fields in dependency from current context.
    User roles and target state are defined in conditions, so we don't need to strongly determine user role.
    Then can be combined to grant more privileges for user in special cases.
    """

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

        return '.'.join([model._meta.app_label, model._meta.model_name, field])

    @staticmethod
    def parse_target(target):
        app_label, model_name, field = target.split('.')
        model = apps.get_model(app_label, model_name)
        return model, field

    @classmethod
    def apply_permissions(cls, permissions, targets, kind):
        """
        apply permissions to targets
        :param permissions:
        :param targets:
        :param kind:
        :return:
        """
        permissions = list(permissions)

        i = 0
        children_map = dict()
        while i < len(permissions):
            perm = permissions[i]

            model, field_name = Permission.parse_target(perm.target)
            if model in children_map:
                children = children_map[model]
            else:
                children = collect_child_models(model, levels=1)
                children_map[model] = children

            # apply permissions to childs, in case of inheritance
            imaginary_permissions = [Permission(permission=perm.permission,
                                                permission_type=perm.permission_type,
                                                condition=perm.condition,
                                                target=Permission.get_target(child, field_name))
                                     for child in children]

            # permissions can be defined both for children and parent, so we need to priority
            # children permissions from automatically generated parent-based permissions.
            perm.image_level = getattr(perm, 'image_level', 0)
            for imaginary_perm in imaginary_permissions:
                imaginary_perm.image_level = perm.image_level + 1

            permissions.extend(imaginary_permissions)

            i += 1

        # order permissions in dependency from their level and complexity of condition
        permissions.sort(key=lambda perm: (perm.image_level, -len(perm.condition), '*' in perm.target))

        allowed_targets = []
        targets = set(targets)
        for perm in permissions:
            if kind == cls.PERMISSIONS.view and perm.permission_type == cls.TYPES.allow:
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
