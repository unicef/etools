from __future__ import absolute_import

from django.db import models
from rest_framework import serializers
from rest_framework.utils import model_meta
from rest_framework_recursive.fields import RecursiveField

from utils.common.serializers.fields import SeparatedReadWriteField
from .utils import collect_parent_models
from .models import Permission


class PermissionsBasedSerializerMixin(object):
    class Meta:
        permission_class = Permission

    def _collect_permissions_targets(self):
        """
        Collect permissions targets based on serializer's model and field name from full serializers tree.
        :return:
        """
        targets = list()

        # Breath-first search
        queue = [self.root]
        while queue:
            node = queue.pop(0)

            if isinstance(node, serializers.ListSerializer):
                queue.append(node.child)
                continue

            if isinstance(node, RecursiveField):
                node_fields = []
            else:
                node_fields = node.fields.values()

            for field in node_fields:
                if isinstance(node, PermissionsBasedSerializerMixin):
                    related_models = collect_parent_models(node.Meta.model)
                    targets.extend(map(
                        lambda model: '{}_{}.{}'.format(model._meta.app_label,
                                                        model._meta.model_name,
                                                        field.field_name),
                        related_models
                    ))

                if isinstance(field, SeparatedReadWriteField):
                    if isinstance(field.read_field, serializers.BaseSerializer):
                        queue.append(field.read_field)
                    if isinstance(field.write_field, serializers.BaseSerializer):
                        queue.append(field.write_field)

                if isinstance(field, serializers.BaseSerializer):
                    queue.append(field)

        return targets

    def _extend_permissions_targets(self, targets):
        """
        Extend permissions targets to using wildcards.
        :param targets:
        :return:
        """
        wildcards = list(set(map(lambda x: '.'.join((x.split('.')[:-1])) + '.*', targets)))
        return targets + wildcards

    def _collect_permissions(self):
        """
        Collect permission objects.
        :return:
        """
        assert self.Meta.permission_class
        assert issubclass(self.Meta.permission_class, Permission)

        targets = self._collect_permissions_targets()
        perms = self._get_permissions_queryset(targets)
        context = self._get_permission_context()
        if context:
            perms = perms.filter_by_context(context)
        return perms

    def _get_permissions_queryset(self, targets):
        targets_query = models.Q(target__in=targets)
        for target in self._extend_permissions_targets(targets):
            targets_query |= models.Q(target__regex=target)

        permissions = self.Meta.permission_class.objects.filter(targets_query)
        return permissions

    def _get_permission_context(self):
        return self.context.get('permission_context', [])

    @property
    def permissions(self):
        """
        Return permission objects related to current serializer.
        :return:
        """
        if not hasattr(self.root, '_permissions'):
            self.root._permissions = list(self._collect_permissions())

        permissions = self.root._permissions
        related_models = tuple(map(lambda model: '{}_{}.'.format(model._meta.app_label, model._meta.model_name),
                                   collect_parent_models(self.Meta.model)))
        permissions = filter(lambda p: p.target.startswith(related_models), permissions)

        context = set(self._get_permission_context())
        permissions = filter(lambda p: set(p.condition).issubset(context), permissions)

        return permissions

    @property
    def _writable_fields(self):
        fields = super(PermissionsBasedSerializerMixin, self)._writable_fields

        allowed_permissions = filter(
            lambda p:
            p.permission == self.Meta.permission_class.PERMISSIONS.edit and
            p.permission_type == self.Meta.permission_class.TYPES.allow,
            self.permissions
        )
        disallowed_permissions = filter(
            lambda p:
            p.permission in [self.Meta.permission_class.PERMISSIONS.edit,
                             self.Meta.permission_class.PERMISSIONS.view] and
            p.permission_type == self.Meta.permission_class.TYPES.disallow,
            self.permissions
        )

        allowed_fields_names = map(lambda p: p.target.split('.')[-1], allowed_permissions)
        disallowed_fields_names = map(lambda p: p.target.split('.')[-1], disallowed_permissions)

        # PK allowed be default
        if allowed_fields_names:
            model = self.Meta.model
            info = model_meta.get_field_info(model)
            allowed_fields_names.extend(['pk', info.pk.name])

        if '*' in allowed_fields_names:
            filtered_fields = fields
        else:
            filtered_fields = filter(lambda f: f.field_name in allowed_fields_names, fields)

        filtered_fields = filter(lambda f: f.field_name not in disallowed_fields_names, filtered_fields)

        return filtered_fields

    @property
    def _readable_fields(self):
        fields = super(PermissionsBasedSerializerMixin, self)._readable_fields

        allowed_permissions = filter(
            lambda p:
            p.permission in [self.Meta.permission_class.PERMISSIONS.edit,
                             self.Meta.permission_class.PERMISSIONS.view] and
            p.permission_type == self.Meta.permission_class.TYPES.allow,
            self.permissions
        )
        disallowed_permissions = filter(
            lambda p:
            p.permission == self.Meta.permission_class.PERMISSIONS.view and
            p.permission_type == self.Meta.permission_class.TYPES.disallow,
            self.permissions
        )

        allowed_fields_names = map(lambda p: p.target.split('.')[-1], allowed_permissions)
        disallowed_fields_names = map(lambda p: p.target.split('.')[-1], disallowed_permissions)

        # PK allowed be default
        if allowed_fields_names:
            model = self.Meta.model
            info = model_meta.get_field_info(model)
            allowed_fields_names.extend(['pk', info.pk.name])

        if '*' in allowed_fields_names:
            filtered_fields = fields
        else:
            filtered_fields = filter(lambda f: f.field_name in allowed_fields_names, fields)

        filtered_fields = filter(lambda f: f.field_name not in disallowed_fields_names, filtered_fields)

        return filtered_fields
