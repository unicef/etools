from django.db import connection
from django.test import TestCase

from rest_framework import serializers

from etools.applications.permissions2.models import Permission
from etools.applications.permissions2.tests.models import Parent, Parent2

from ..serializers import PermissionsBasedSerializerMixin


class TestPermissionModel(TestCase):
    def test_filter_for_wildcards(self):
        permission = Permission.objects.create(permission=Permission.PERMISSIONS.view, target='permissions2.parent.*')

        targets = ['permissions2.parent.1', 'permissions2.parent.2', 'permissions2.parent.3']
        permissions = Permission.objects.filter_by_targets(targets)

        self.assertSequenceEqual(permissions, [permission])

    def test_apply_permissions_different_kinds(self):
        Permission.objects.create(permission=Permission.PERMISSIONS.view, target='permissions2.parent.1')
        Permission.objects.create(permission=Permission.PERMISSIONS.edit, target='permissions2.parent.3')

        targets = ['permissions2.parent.1', 'permissions2.parent.2', 'permissions2.parent.3']

        allowed_targets = Permission.apply_permissions(Permission.objects.all(), targets,
                                                       Permission.PERMISSIONS.view)
        self.assertSequenceEqual(allowed_targets, ['permissions2.parent.1', 'permissions2.parent.3'])

        allowed_targets = Permission.apply_permissions(Permission.objects.all(), targets,
                                                       Permission.PERMISSIONS.edit)
        self.assertSequenceEqual(allowed_targets, ['permissions2.parent.3'])

    def test_apply_permissions_order(self):
        Permission.objects.create(permission=Permission.PERMISSIONS.view, target='permissions2.parent.*')
        Permission.objects.create(permission=Permission.PERMISSIONS.view, target='permissions2.parent.1',
                                  permission_type=Permission.TYPES.disallow)
        Permission.objects.create(permission=Permission.PERMISSIONS.view, target='permissions2.parent.2',
                                  permission_type=Permission.TYPES.disallow, condition=['condition1'])

        targets = ['permissions2.parent.1', 'permissions2.parent.2', 'permissions2.parent.3']

        allowed_targets = Permission.apply_permissions(Permission.objects.all(), targets,
                                                       Permission.PERMISSIONS.view)
        self.assertSequenceEqual(allowed_targets, ['permissions2.parent.3'])

        Permission.objects.create(permission=Permission.PERMISSIONS.view, target='permissions2.parent.2',
                                  permission_type=Permission.TYPES.allow, condition=['condition1', 'condition2'])

        allowed_targets = Permission.apply_permissions(Permission.objects.all(), targets,
                                                       Permission.PERMISSIONS.view)
        self.assertSequenceEqual(allowed_targets, ['permissions2.parent.2', 'permissions2.parent.3'])


class ParentSerializer(PermissionsBasedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Parent
        fields = ['id', 'field1', 'field2']


class Parent2Serializer(PermissionsBasedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Parent2
        fields = ['id', 'field1', 'field2', 'field3']


class TestInheritedModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        # We disable synchronisation of test models. So we need to create it manually.
        with connection.schema_editor() as editor:
            editor.create_model(Parent)
            editor.create_model(Parent2)

    def test_inherited_permissions(self):
        Permission.objects.create(permission='view', target='permissions2.parent.field1')
        Permission.objects.create(permission='view', target='permissions2.parent2.field3')

        parent = Parent2.objects.create(field1=1, field2=2, field3=3)

        serializer = Parent2Serializer(instance=parent)
        self.assertDictEqual(serializer.data, {
            'id': parent.id,
            'field1': 1,
            'field3': 3,
        })

    def test_overridden_permissions(self):
        parent = Parent2.objects.create(field1=1, field2=2, field3=3)

        Permission.objects.create(permission='view', target='permissions2.parent.field1')

        serializer = Parent2Serializer(instance=parent)
        self.assertDictEqual(serializer.data, {
            'id': parent.id,
            'field1': 1,
        })

        Permission.objects.create(permission='view', target='permissions2.parent2.field1', permission_type='disallow')

        serializer = Parent2Serializer(instance=parent)
        self.assertDictEqual(serializer.data, {})

        serializer = ParentSerializer(instance=parent)
        self.assertDictEqual(serializer.data, {
            'id': parent.id,
            'field1': 1
        })

    def test_forbid_permissions(self):
        parent = Parent2.objects.create(field1=1, field2=2, field3=3)

        Permission.objects.create(permission='edit', target='permissions2.parent.field1')
        Permission.objects.create(permission='edit', target='permissions2.parent2.field1', permission_type='disallow')

        serializer = Parent2Serializer(instance=parent)
        self.assertDictEqual(serializer.data, {
            'id': parent.id,
            'field1': 1,
        })

        Permission.objects.create(permission='view', target='permissions2.parent2.field1', permission_type='disallow')

        serializer = Parent2Serializer(instance=parent)
        self.assertDictEqual(serializer.data, {})
