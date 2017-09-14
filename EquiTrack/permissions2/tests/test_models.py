from django.test import TestCase

from ..models import Permission


class TestPermissionModel(TestCase):
    def test_filter_for_wildcards(self):
        permission = Permission.objects.create(permission=Permission.PERMISSIONS.view, target='test_test.*')

        targets = ['test_test.1', 'test_test.2', 'test_test.3']
        permissions = Permission.objects.filter_by_targets(targets)

        self.assertSequenceEqual(permissions, [permission])

    def test_apply_permissions_different_kinds(self):
        Permission.objects.create(permission=Permission.PERMISSIONS.view, target='test_test.1')
        Permission.objects.create(permission=Permission.PERMISSIONS.edit, target='test_test.3')

        targets = ['test_test.1', 'test_test.2', 'test_test.3']

        allowed_targets = Permission.apply_permissions(Permission.objects.all(), targets,
                                                       Permission.PERMISSIONS.view)
        self.assertSequenceEqual(allowed_targets, ['test_test.1', 'test_test.3'])

        allowed_targets = Permission.apply_permissions(Permission.objects.all(), targets,
                                                       Permission.PERMISSIONS.edit)
        self.assertSequenceEqual(allowed_targets, ['test_test.3'])

    def test_apply_permissions_order(self):
        Permission.objects.create(permission=Permission.PERMISSIONS.view, target='test_test.*')
        Permission.objects.create(permission=Permission.PERMISSIONS.view, target='test_test.1',
                                  permission_type=Permission.TYPES.disallow)
        Permission.objects.create(permission=Permission.PERMISSIONS.view, target='test_test.2',
                                  permission_type=Permission.TYPES.disallow, condition=['condition1'])

        targets = ['test_test.1', 'test_test.2', 'test_test.3']

        allowed_targets = Permission.apply_permissions(Permission.objects.all(), targets,
                                                       Permission.PERMISSIONS.view)
        self.assertSequenceEqual(allowed_targets, ['test_test.3'])

        Permission.objects.create(permission=Permission.PERMISSIONS.view, target='test_test.2',
                                  permission_type=Permission.TYPES.allow, condition=['condition1', 'condition2'])

        allowed_targets = Permission.apply_permissions(Permission.objects.all(), targets,
                                                       Permission.PERMISSIONS.view)
        self.assertSequenceEqual(allowed_targets, ['test_test.2', 'test_test.3'])
