from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Permission

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory
from etools.applications.vision.admin import VisionSyncLogAdmin
from etools.applications.vision.models import VisionSyncLog


class MockRequest:
    pass


class TestVisionSyncLogAdminPermissions(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        site = AdminSite()
        cls.admin = VisionSyncLogAdmin(VisionSyncLog, site)
        cls.request = MockRequest()

        # Permissions
        cls.perm_view = Permission.objects.get(codename='view_visionsynclog')
        cls.perm_add = Permission.objects.get(codename='add_visionsynclog')
        cls.perm_change = Permission.objects.get(codename='change_visionsynclog')
        cls.perm_delete = Permission.objects.get(codename='delete_visionsynclog')

    def test_superuser_can_view_and_modify(self):
        user = UserFactory(is_superuser=True, is_staff=True)
        self.request.user = user

        self.assertTrue(self.admin.has_view_permission(self.request))
        self.assertTrue(self.admin.has_add_permission(self.request))
        self.assertTrue(self.admin.has_change_permission(self.request))
        self.assertTrue(self.admin.has_delete_permission(self.request))

    def test_staff_with_model_perms_can_view_and_modify(self):
        user = UserFactory(is_superuser=False, is_staff=True)
        user.user_permissions.add(self.perm_add, self.perm_change, self.perm_delete, self.perm_view)
        self.request.user = user

        self.assertTrue(self.admin.has_view_permission(self.request))
        self.assertTrue(self.admin.has_add_permission(self.request))
        self.assertTrue(self.admin.has_change_permission(self.request))
        self.assertTrue(self.admin.has_delete_permission(self.request))

    def test_view_only_user_can_only_view(self):
        user = UserFactory(is_superuser=False, is_staff=False)
        user.user_permissions.add(self.perm_view)
        self.request.user = user

        self.assertTrue(self.admin.has_view_permission(self.request))
        self.assertFalse(self.admin.has_add_permission(self.request))
        self.assertFalse(self.admin.has_change_permission(self.request))
        self.assertFalse(self.admin.has_delete_permission(self.request))
        self.assertTrue(self.admin.has_module_permission(self.request))

    def test_user_without_staff_and_without_perm_cannot_see(self):
        user = UserFactory(is_superuser=False, is_staff=False)
        self.request.user = user

        self.assertFalse(self.admin.has_view_permission(self.request))
        self.assertFalse(self.admin.has_module_permission(self.request))
