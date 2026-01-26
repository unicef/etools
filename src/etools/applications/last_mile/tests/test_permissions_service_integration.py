from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import (
    LIST_INTERESTED_LASTMILE_PERMS,
    LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE,
)
from etools.applications.last_mile.services.permissions_service import LMSMPermissionsService
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.users.models import Realm
from etools.applications.users.tests.factories import CountryFactory, GroupFactory, UserFactory


class TestLMSMPermissionsServiceIntegration(BaseTenantTestCase):

    def setUp(self):
        super().setUp()
        self.service = LMSMPermissionsService()
        self.user = UserFactory()

        self.co_admin_group = GroupFactory(name="LMSM CO Admin")
        self.hq_admin_group = GroupFactory(name="LMSM HQ Admin")

        self._create_real_permissions()

        self.organization = OrganizationFactory()
        self.country = CountryFactory()

    def _create_real_permissions(self):
        User = get_user_model()
        content_type = ContentType.objects.get_for_model(User)

        for perm_codename in LIST_INTERESTED_LASTMILE_PERMS:
            Permission.objects.get_or_create(
                codename=perm_codename,
                defaults={
                    'name': f"Can {perm_codename.replace('_', ' ')}",
                    'content_type': content_type
                }
            )

    def test_assign_permissions_for_co_admin(self):
        self.assertEqual(self.user.user_permissions.count(), 0)

        self.service.assign_permissions_for_co_admin(self.user)

        user_perms = set(self.user.user_permissions.values_list('codename', flat=True))
        expected_perms = set(LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE)

        self.assertEqual(user_perms, expected_perms)

        approve_perms = set(LIST_INTERESTED_LASTMILE_PERMS) - set(LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE)
        for perm_codename in approve_perms:
            self.assertFalse(
                self.user.user_permissions.filter(codename=perm_codename).exists(),
                f"User should not have {perm_codename} permission"
            )

    def test_assign_permissions_for_hq_admin(self):
        self.assertEqual(self.user.user_permissions.count(), 0)

        self.service.assign_permissions_for_hq_admin(self.user)

        user_perms = set(self.user.user_permissions.values_list('codename', flat=True))
        expected_perms = set(LIST_INTERESTED_LASTMILE_PERMS)

        self.assertEqual(user_perms, expected_perms)

        for perm_codename in LIST_INTERESTED_LASTMILE_PERMS:
            self.assertTrue(
                self.user.user_permissions.filter(codename=perm_codename).exists(),
                f"User should have {perm_codename} permission"
            )

    def test_realm_creation_assigns_permissions(self):
        self.assertEqual(self.user.user_permissions.count(), 0)

        # Create CO Admin realm - this should trigger signal and assign permissions
        Realm.objects.create(
            user=self.user,
            group=self.co_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=True
        )

        # Reload user to get fresh permissions
        self.user.refresh_from_db()

        # Check permissions were assigned
        user_perms = set(self.user.user_permissions.values_list('codename', flat=True))
        expected_perms = set(LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE)

        self.assertEqual(user_perms, expected_perms)

    def test_realm_deactivation_removes_permissions(self):
        realm = Realm.objects.create(
            user=self.user,
            group=self.hq_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=True
        )

        self.user.refresh_from_db()
        self.assertGreater(self.user.user_permissions.count(), 0)
        initial_perms = set(self.user.user_permissions.values_list('codename', flat=True))
        self.assertEqual(initial_perms, set(LIST_INTERESTED_LASTMILE_PERMS))

        realm.is_active = False
        realm.save()

        self.user.refresh_from_db()
        self.assertEqual(self.user.user_permissions.count(), 0)

    def test_realm_reactivation_reassigns_permissions(self):
        realm = Realm.objects.create(
            user=self.user,
            group=self.co_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=False
        )

        self.assertEqual(self.user.user_permissions.count(), 0)

        realm.is_active = True
        realm.save()

        self.user.refresh_from_db()
        user_perms = set(self.user.user_permissions.values_list('codename', flat=True))
        expected_perms = set(LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE)

        self.assertEqual(user_perms, expected_perms)

    def test_realm_deletion_removes_permissions(self):
        realm = Realm.objects.create(
            user=self.user,
            group=self.hq_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=True
        )

        self.user.refresh_from_db()
        self.assertGreater(self.user.user_permissions.count(), 0)

        realm.delete()

        self.user.refresh_from_db()
        self.assertEqual(self.user.user_permissions.count(), 0)

    def test_upgrade_from_co_to_hq(self):
        Realm.objects.create(
            user=self.user,
            group=self.co_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=True
        )

        self.user.refresh_from_db()
        user_perms = set(self.user.user_permissions.values_list('codename', flat=True))
        self.assertEqual(user_perms, set(LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE))

        Realm.objects.create(
            user=self.user,
            group=self.hq_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=True
        )

        self.user.refresh_from_db()
        user_perms = set(self.user.user_permissions.values_list('codename', flat=True))
        self.assertEqual(user_perms, set(LIST_INTERESTED_LASTMILE_PERMS))

    def test_downgrade_from_hq_to_co(self):
        Realm.objects.create(
            user=self.user,
            group=self.co_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=True
        )

        hq_realm = Realm.objects.create(
            user=self.user,
            group=self.hq_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=True
        )

        self.user.refresh_from_db()
        user_perms = set(self.user.user_permissions.values_list('codename', flat=True))
        self.assertEqual(user_perms, set(LIST_INTERESTED_LASTMILE_PERMS))

        hq_realm.is_active = False
        hq_realm.save()

        self.user.refresh_from_db()
        user_perms = set(self.user.user_permissions.values_list('codename', flat=True))
        self.assertEqual(user_perms, set(LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE))

    def test_complex_scenario_multiple_realm_changes(self):
        self.assertEqual(self.user.user_permissions.count(), 0)

        co_realm = Realm.objects.create(
            user=self.user,
            group=self.co_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=True
        )

        self.user.refresh_from_db()
        self.assertEqual(
            set(self.user.user_permissions.values_list('codename', flat=True)),
            set(LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE)
        )

        hq_realm = Realm.objects.create(
            user=self.user,
            group=self.hq_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=True
        )

        self.user.refresh_from_db()
        self.assertEqual(
            set(self.user.user_permissions.values_list('codename', flat=True)),
            set(LIST_INTERESTED_LASTMILE_PERMS)
        )

        co_realm.delete()

        self.user.refresh_from_db()
        self.assertEqual(
            set(self.user.user_permissions.values_list('codename', flat=True)),
            set(LIST_INTERESTED_LASTMILE_PERMS)
        )

        hq_realm.is_active = False
        hq_realm.save()

        self.user.refresh_from_db()
        self.assertEqual(self.user.user_permissions.count(), 0)

        hq_realm.is_active = True
        hq_realm.save()

        self.user.refresh_from_db()
        self.assertEqual(
            set(self.user.user_permissions.values_list('codename', flat=True)),
            set(LIST_INTERESTED_LASTMILE_PERMS)
        )

    def test_multiple_users_independent_permissions(self):
        user1 = self.user
        user2 = UserFactory()

        realm1 = Realm.objects.create(
            user=user1,
            group=self.co_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=True
        )

        Realm.objects.create(
            user=user2,
            group=self.hq_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=True
        )

        user1.refresh_from_db()
        user2.refresh_from_db()

        user1_perms = set(user1.user_permissions.values_list('codename', flat=True))
        user2_perms = set(user2.user_permissions.values_list('codename', flat=True))

        self.assertEqual(user1_perms, set(LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE))
        self.assertEqual(user2_perms, set(LIST_INTERESTED_LASTMILE_PERMS))

        realm1.is_active = False
        realm1.save()

        user1.refresh_from_db()
        user2.refresh_from_db()

        self.assertEqual(user1.user_permissions.count(), 0)
        self.assertEqual(
            set(user2.user_permissions.values_list('codename', flat=True)),
            set(LIST_INTERESTED_LASTMILE_PERMS)
        )

    def test_idempotent_permission_assignment(self):
        self.service.assign_permissions_for_co_admin(self.user)
        self.service.assign_permissions_for_co_admin(self.user)
        self.service.assign_permissions_for_co_admin(self.user)

        user_perms = list(self.user.user_permissions.values_list('codename', flat=True))
        expected_perms = LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE

        self.assertEqual(len(user_perms), len(expected_perms))

        for perm in expected_perms:
            self.assertEqual(user_perms.count(perm), 1, f"Permission {perm} should appear exactly once")

    def test_permission_removal_with_no_permissions(self):
        self.assertEqual(self.user.user_permissions.count(), 0)

        try:
            self.service.remove_all_lmsm_permissions(self.user)
            self.service.remove_approve_permissions(self.user)
        except Exception as e:
            self.fail(f"Removing permissions from user with no permissions raised: {e}")

        self.assertEqual(self.user.user_permissions.count(), 0)

    def test_handle_missing_permission_gracefully(self):
        Permission.objects.filter(codename=LIST_INTERESTED_LASTMILE_PERMS[0]).delete()

        try:
            self.service.assign_permissions_for_hq_admin(self.user)
        except Exception as e:
            self.fail(f"Service raised an exception for missing permission: {e}")

        user_perms = set(self.user.user_permissions.values_list('codename', flat=True))
        expected_perms = set(LIST_INTERESTED_LASTMILE_PERMS[1:])  # All except first

        self.assertEqual(user_perms, expected_perms)

    def test_concurrent_realm_operations(self):
        realm1 = Realm.objects.create(
            user=self.user,
            group=self.co_admin_group,
            country=self.country,
            organization=self.organization,
            is_active=True
        )

        realm2 = Realm.objects.create(
            user=self.user,
            group=self.co_admin_group,
            country=self.country,
            organization=OrganizationFactory(),  # Different org
            is_active=True
        )

        self.user.refresh_from_db()
        user_perms = set(self.user.user_permissions.values_list('codename', flat=True))
        self.assertEqual(user_perms, set(LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE))

        realm1.delete()

        self.user.refresh_from_db()
        user_perms = set(self.user.user_permissions.values_list('codename', flat=True))
        self.assertEqual(user_perms, set(LIST_INTERESTED_LASTMILE_PERMS_WITHOUT_APPROVE))

        realm2.delete()

        self.user.refresh_from_db()
        self.assertEqual(self.user.user_permissions.count(), 0)
