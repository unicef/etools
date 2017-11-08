from __future__ import absolute_import

from django.db import models

from rest_framework import serializers
from rest_framework.utils import model_meta
from rest_framework_recursive.fields import RecursiveField

from utils.common.serializers.fields import SeparatedReadWriteField
from utils.common.serializers.mixins import UserContextSerializerMixin
from utils.permissions.models.models import BasePermission
from utils.permissions.utils import collect_parent_models


class PermissionsBasedSerializerMixin(UserContextSerializerMixin):
    class Meta:
        permission_class = None

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
                    targets.extend(map(lambda model: model + '.' + field.field_name, related_models))

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
        assert issubclass(self.Meta.permission_class, BasePermission)

        targets = self._collect_permissions_targets()
        perms = self._get_permissions_queryset(targets).filter(user=self.get_user())
        return perms

    def _get_permissions_queryset(self, targets):
        targets_query = models.Q(target__in=targets)
        for target in self._extend_permissions_targets(targets):
            targets_query |= models.Q(target__regex=target)

        permissions = self.Meta.permission_class.objects.filter(targets_query)
        return permissions

    @property
    def permissions(self):
        """
        Return permission objects related to current serializer.
        :return:
        """
        if not hasattr(self.root, '_permissions'):
            self.root._permissions = list(self._collect_permissions())

        permissions = self.root._permissions
        related_models = tuple(map(lambda x: x + '.', collect_parent_models(self.Meta.model)))
        permissions = filter(lambda p: p.target.startswith(related_models), permissions)
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


class StatusPermissionsBasedSerializerMixin(PermissionsBasedSerializerMixin):
    def _collect_permissions(self):
        targets = self._collect_permissions_targets()
        # We can't use self.instance to get root instance because this field return queryset
        # when root serializer used many instances.
        instance = self.context.get('instance')
        perms = self._get_permissions_queryset(targets).filter(user=self.get_user(), instance=instance)
        return perms

    @property
    def permissions(self):
        permissions = super(StatusPermissionsBasedSerializerMixin, self).permissions

        instance = self.context.get('instance')
        instance_status = instance.status if instance else self.Meta.permission_class.STATUSES.new
        permissions = filter(lambda p: p.instance_status == instance_status, permissions)

        return permissions


class StatusPermissionsBasedRootListSerializer(serializers.ListSerializer):
    def _collect_permissions(self, instances):
        """
        Collect permission objects.
        :return:
        """
        targets = self.child._collect_permissions_targets()
        perms = self.child._get_permissions_queryset(targets).filter(
            user=self.child.get_user(), instance__in=instances)
        return perms

    def to_representation(self, data):
        iterable = data.all() if isinstance(data, models.Manager) else data
        self.root._permissions = list(self._collect_permissions(iterable))

        return super(StatusPermissionsBasedRootListSerializer, self).to_representation(iterable)


class StatusPermissionsBasedRootSerializerMixin(StatusPermissionsBasedSerializerMixin):
    class Meta(StatusPermissionsBasedSerializerMixin.Meta):
        list_serializer_class = StatusPermissionsBasedRootListSerializer

    def save(self, **kwargs):
        old_status = self.instance.status if self.instance else None

        self.context['instance'] = self.instance
        instance = super(StatusPermissionsBasedRootSerializerMixin, self).save(**kwargs)
        del self.context['instance']

        if old_status != instance.status:
            delattr(self.root, '_permissions')
        return instance

    def to_internal_value(self, data):
        self.context['instance'] = self.instance
        ret = super(StatusPermissionsBasedRootSerializerMixin, self).to_internal_value(data)
        del self.context['instance']
        return ret

    def to_representation(self, instance):
        self.context['instance'] = instance
        ret = super(StatusPermissionsBasedRootSerializerMixin, self).to_representation(instance)
        del self.context['instance']
        return ret
