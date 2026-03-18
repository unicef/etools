from django.contrib.contenttypes.models import ContentType
from django.db import connection

from etools.applications.audit_log.models import AuditLogEntry
from etools.applications.audit_log.service import audit_log, AUDIT_LOG_SWITCH
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.environment.tests.factories import TenantSwitchFactory
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import UserFactory


class TestAuditLogFunction(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        super().setUp()
        self.switch = TenantSwitchFactory(name=AUDIT_LOG_SWITCH, active=True)
        self.switch.countries.add(connection.tenant)

    def tearDown(self):
        self.switch.flush()
        super().tearDown()

    def test_create_logs_all_fields(self):
        partner = PartnerFactory()
        audit_log(partner, 'CREATE', user=self.user)

        entry = AuditLogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(PartnerOrganization),
            object_id=str(partner.pk),
        ).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.action, AuditLogEntry.ACTION_CREATE)
        self.assertEqual(entry.user, self.user)
        self.assertIsNotNone(entry.new_values)
        self.assertIsNone(entry.old_values)
        self.assertIsNone(entry.changed_fields)

    def test_create_with_custom_fields(self):
        partner = PartnerFactory()
        audit_log(partner, 'CREATE', user=self.user, fields=['shared_with', 'net_ct_cy'])

        entry = AuditLogEntry.objects.first()
        self.assertEqual(set(entry.new_values.keys()), {'shared_with', 'net_ct_cy'})

    def test_update_with_old_instance(self):
        partner = PartnerFactory()
        old_instance = PartnerOrganization.objects.get(pk=partner.pk)

        partner.shared_with = ['USAID']
        partner.save()

        audit_log(partner, 'UPDATE', user=self.user, old_instance=old_instance)

        entry = AuditLogEntry.objects.filter(
            action=AuditLogEntry.ACTION_UPDATE,
        ).first()
        self.assertIsNotNone(entry)
        self.assertIn('shared_with', entry.changed_fields)
        self.assertIn('shared_with', entry.old_values)
        self.assertIn('shared_with', entry.new_values)

    def test_update_no_changes_skipped(self):
        partner = PartnerFactory()
        old_instance = PartnerOrganization.objects.get(pk=partner.pk)

        # Save without changes
        partner.save()

        audit_log(partner, 'UPDATE', user=self.user, old_instance=old_instance)

        self.assertEqual(
            AuditLogEntry.objects.filter(action=AuditLogEntry.ACTION_UPDATE).count(),
            0,
        )

    def test_update_explicit_values(self):
        partner = PartnerFactory()

        audit_log(
            partner, 'UPDATE', user=self.user,
            changed_fields=['partner_organizations'],
            old_values={'partner_organizations': [1, 2]},
            new_values={'partner_organizations': [1, 2, 3]},
        )

        entry = AuditLogEntry.objects.first()
        self.assertEqual(entry.action, AuditLogEntry.ACTION_UPDATE)
        self.assertEqual(entry.changed_fields, ['partner_organizations'])
        self.assertEqual(entry.old_values, {'partner_organizations': [1, 2]})
        self.assertEqual(entry.new_values, {'partner_organizations': [1, 2, 3]})

    def test_update_without_old_instance_or_values_skipped(self):
        partner = PartnerFactory()
        audit_log(partner, 'UPDATE', user=self.user)

        self.assertEqual(AuditLogEntry.objects.count(), 0)

    def test_delete_logs_old_values(self):
        partner = PartnerFactory()
        partner_pk = partner.pk

        audit_log(partner, 'DELETE', user=self.user)

        entry = AuditLogEntry.objects.filter(
            object_id=str(partner_pk),
            action=AuditLogEntry.ACTION_DELETE,
        ).first()
        self.assertIsNotNone(entry)
        self.assertIsNotNone(entry.old_values)
        self.assertIsNone(entry.new_values)
        self.assertIsNone(entry.changed_fields)

    def test_soft_delete(self):
        partner = PartnerFactory()
        audit_log(partner, 'SOFT_DELETE', user=self.user)

        entry = AuditLogEntry.objects.first()
        self.assertEqual(entry.action, AuditLogEntry.ACTION_SOFT_DELETE)
        self.assertIsNotNone(entry.old_values)

    def test_description_saved(self):
        partner = PartnerFactory()
        audit_log(partner, 'CREATE', user=self.user, description='Bulk import')

        entry = AuditLogEntry.objects.first()
        self.assertEqual(entry.description, 'Bulk import')

    def test_user_falls_back_to_current_user(self):
        partner = PartnerFactory()

        # No user passed — should use None (no request context in tests)
        audit_log(partner, 'CREATE')

        entry = AuditLogEntry.objects.first()
        self.assertIsNotNone(entry)
        self.assertIsNone(entry.user)

    def test_exception_does_not_propagate(self):
        """audit_log should never break the caller, even on errors."""
        from unittest.mock import patch

        partner = PartnerFactory()
        # Force an error by making the DB call fail
        with patch.object(AuditLogEntry.objects, 'create', side_effect=RuntimeError('DB down')):
            audit_log(partner, 'CREATE', user=self.user)
        # If we get here, no exception was raised
        self.assertEqual(AuditLogEntry.objects.count(), 0)

    def test_switch_disabled_skips_logging(self):
        """No audit entries created when tenant switch is off."""
        self.switch.active = False
        self.switch.save()
        self.switch.flush()

        partner = PartnerFactory()
        audit_log(partner, 'CREATE', user=self.user)

        self.assertEqual(AuditLogEntry.objects.count(), 0)
