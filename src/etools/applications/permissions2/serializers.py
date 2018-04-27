from rest_framework import serializers
from rest_framework.utils import model_meta
from rest_framework_recursive.fields import RecursiveField

from etools.applications.permissions2.models import Permission
from etools.applications.utils.common.serializers.fields import SeparatedReadWriteField


class PermissionsBasedSerializerMixin(object):
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
                # stop too deep recursion
                node_fields = []
            else:
                node_fields = node.fields.values()

            for field in node_fields:
                if isinstance(node, PermissionsBasedSerializerMixin):
                    targets.append(Permission.get_target(node.Meta.model, field))

                if isinstance(field, SeparatedReadWriteField):
                    if isinstance(field.read_field, serializers.BaseSerializer):
                        queue.append(field.read_field)
                    if isinstance(field.write_field, serializers.BaseSerializer):
                        queue.append(field.write_field)

                if isinstance(field, serializers.BaseSerializer):
                    queue.append(field)

        return targets

    def _collect_permissions(self):
        """
        Collect permission objects.
        :return:
        """
        targets = self._collect_permissions_targets()
        perms = self._get_permissions_queryset(targets)
        context = self._get_permission_context()
        perms = perms.filter_by_context(context)
        return perms

    def _get_permissions_queryset(self, targets):
        return Permission.objects.filter_by_targets(targets)

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

        return self.root._permissions

    def _filter_fields_by_permissions(self, fields, permissions_kind):
        """
        Filter serializer fields by permissions kind
        :param fields: serializer fields list
        :param permissions_kind: edit/view
        :return: fields allowed to interact with
        """
        model = self.Meta.model
        targets_map = {Permission.get_target(model, field): field for field in fields}

        pk_fields = []
        pk_target = Permission.get_target(model, 'pk')
        if pk_target in targets_map:
            pk_fields.append(targets_map.pop(pk_target))

        pk_field = model_meta.get_field_info(model).pk
        pk_target = Permission.get_target(model, pk_field)
        if pk_target in targets_map:
            pk_fields.append(targets_map.pop(pk_target))

        allowed_targets = Permission.apply_permissions(self.permissions, targets_map.keys(), permissions_kind)

        allowed_fields = list(map(lambda target: targets_map[target], allowed_targets))

        if allowed_fields:
            allowed_fields.extend(pk_fields)

        return allowed_fields

    @property
    def _writable_fields(self):
        fields = super(PermissionsBasedSerializerMixin, self)._writable_fields

        return self._filter_fields_by_permissions(fields, Permission.PERMISSIONS.edit)

    @property
    def _readable_fields(self):
        fields = super(PermissionsBasedSerializerMixin, self)._readable_fields

        return self._filter_fields_by_permissions(fields, Permission.PERMISSIONS.view)
