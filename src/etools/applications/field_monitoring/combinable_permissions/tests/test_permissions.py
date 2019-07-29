from django.test import TestCase

from rest_framework.permissions import BasePermission

from etools.applications.field_monitoring.combinable_permissions.permissions import PermissionQ


class TruePermission(BasePermission):
    def has_permission(self, request, view):
        return True


class FalsePermission(BasePermission):
    def has_permission(self, request, view):
        return False


class TestPermissions(TestCase):
    def _test_permission(self, permission, expected_result):
        self.assertEqual(permission.has_permission(None, None), expected_result)

    def test_single_true(self):
        self._test_permission(PermissionQ(TruePermission), True)

    def test_single_false(self):
        self._test_permission(PermissionQ(FalsePermission), False)

    def test_constructor(self):
        self._test_permission(PermissionQ(TruePermission, TruePermission), True)
        self._test_permission(PermissionQ(TruePermission, FalsePermission), False)
        self._test_permission(PermissionQ(FalsePermission, TruePermission), False)
        self._test_permission(PermissionQ(FalsePermission, FalsePermission), False)

    def test_logical_and(self):
        self._test_permission(PermissionQ(TruePermission) & PermissionQ(TruePermission), True)
        self._test_permission(PermissionQ(TruePermission) & PermissionQ(FalsePermission), False)
        self._test_permission(PermissionQ(FalsePermission) & PermissionQ(TruePermission), False)
        self._test_permission(PermissionQ(FalsePermission) & PermissionQ(FalsePermission), False)

    def test_logical_or(self):
        self._test_permission(PermissionQ(TruePermission) | PermissionQ(TruePermission), True)
        self._test_permission(PermissionQ(TruePermission) | PermissionQ(FalsePermission), True)
        self._test_permission(PermissionQ(FalsePermission) | PermissionQ(TruePermission), True)
        self._test_permission(PermissionQ(FalsePermission) | PermissionQ(FalsePermission), False)

    def test_logical_not(self):
        self._test_permission(~PermissionQ(TruePermission), False)
        self._test_permission(~PermissionQ(FalsePermission), True)
