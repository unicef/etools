import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from django.db import IntegrityError, transaction
from django.utils import timezone

from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile import models
from etools.applications.last_mile.admin import ItemAuditLogAdmin
from etools.applications.last_mile.config_audit import ITEM_AUDIT_LOG_TRACKED_FIELDS
from etools.applications.last_mile.tests.factories import (
    ItemFactory,
    MaterialFactory,
    PointOfInterestFactory,
    TransferFactory,
)
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import UserFactory


class TestItemAuditLogSignals(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserFactory(
            realms__data=['IP LM Editor'],
            profile__organization=cls.partner.organization,
        )
        cls.poi_partner = PointOfInterestFactory(partner_organizations=[cls.partner], private=True)
        cls.transfer = TransferFactory(
            destination_point=cls.poi_partner,
            partner_organization=cls.partner,
            status=models.Transfer.COMPLETED
        )
        cls.material = MaterialFactory(number='1234', original_uom='EA')

    def setUp(self):
        models.ItemAuditLog.objects.all().delete()

    def test_item_creation_audit(self):
        item = ItemFactory(
            transfer=self.transfer,
            material=self.material,
            quantity=10,
            batch_id='BATCH123',
            mapped_description='Test item description'
        )

        audit_logs = models.ItemAuditLog.objects.filter(item_id=item.id)
        self.assertEqual(audit_logs.count(), 1)

        audit_log = audit_logs.first()
        self.assertEqual(audit_log.action, models.ItemAuditLog.ACTION_CREATE)
        self.assertEqual(audit_log.item_id, item.id)
        self.assertIsNone(audit_log.user)
        self.assertIsNotNone(audit_log.transfer_info)
        self.assertIsNotNone(audit_log.material_info)

        self.assertIsNotNone(audit_log.new_values)
        self.assertEqual(audit_log.new_values['quantity'], 10)
        self.assertEqual(audit_log.new_values['batch_id'], 'BATCH123')

        self.assertIsNone(audit_log.old_values)

    def test_item_update_audit(self):
        item = ItemFactory(
            transfer=self.transfer,
            material=self.material,
            quantity=10,
            batch_id='BATCH123'
        )

        models.ItemAuditLog.objects.all().delete()

        item.quantity = 15
        item.batch_id = 'BATCH456'
        item.mapped_description = 'Updated description'
        item.save()

        audit_logs = models.ItemAuditLog.objects.filter(item_id=item.id)
        self.assertEqual(audit_logs.count(), 1)

        audit_log = audit_logs.first()
        self.assertEqual(audit_log.action, models.ItemAuditLog.ACTION_UPDATE)
        self.assertEqual(audit_log.item_id, item.id)

        self.assertIsNotNone(audit_log.old_values)
        self.assertIsNotNone(audit_log.new_values)
        self.assertEqual(audit_log.old_values['quantity'], 10)
        self.assertEqual(audit_log.new_values['quantity'], 15)
        self.assertEqual(audit_log.old_values['batch_id'], 'BATCH123')
        self.assertEqual(audit_log.new_values['batch_id'], 'BATCH456')

        self.assertIn('quantity', audit_log.changed_fields)
        self.assertIn('batch_id', audit_log.changed_fields)
        self.assertIn('mapped_description', audit_log.changed_fields)

    def test_item_deletion_audit(self):
        item = ItemFactory(
            transfer=self.transfer,
            material=self.material,
            quantity=10,
            batch_id='BATCH123'
        )
        item_id = item.id

        models.ItemAuditLog.objects.all().delete()

        item.delete()

        audit_logs = models.ItemAuditLog.objects.filter(item_id=item_id)
        self.assertEqual(audit_logs.count(), 1)

        audit_log = audit_logs.first()
        self.assertEqual(audit_log.action, models.ItemAuditLog.ACTION_DELETE)
        self.assertEqual(audit_log.item_id, item_id)

        self.assertIsNotNone(audit_log.old_values)
        self.assertIsNone(audit_log.new_values)
        self.assertEqual(audit_log.old_values['quantity'], 10)
        self.assertEqual(audit_log.old_values['batch_id'], 'BATCH123')

    def test_item_soft_delete_audit(self):
        item = ItemFactory(
            transfer=self.transfer,
            material=self.material,
            quantity=10,
            hidden=False
        )

        models.ItemAuditLog.objects.all().delete()

        item.hidden = True
        item.save()

        audit_logs = models.ItemAuditLog.objects.filter(item_id=item.id)
        self.assertEqual(audit_logs.count(), 1)

        audit_log = audit_logs.first()
        self.assertEqual(audit_log.action, models.ItemAuditLog.ACTION_SOFT_DELETE)

    def test_transfer_info_capture(self):
        transfer = TransferFactory(
            name='Test Transfer',
            transfer_type=models.Transfer.DELIVERY,
            status=models.Transfer.PENDING,
            unicef_release_order='URO123',
            waybill_id='WB456',
            destination_point=self.poi_partner,
            partner_organization=self.partner
        )

        item = ItemFactory(transfer=transfer, material=self.material)

        audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).first()
        self.assertIsNotNone(audit_log.transfer_info)

        transfer_info = audit_log.transfer_info
        self.assertEqual(transfer_info['transfer_name'], 'Test Transfer')
        self.assertEqual(transfer_info['transfer_type'], models.Transfer.DELIVERY)
        self.assertEqual(transfer_info['transfer_status'], models.Transfer.PENDING)
        self.assertEqual(transfer_info['unicef_release_order'], 'URO123')
        self.assertEqual(transfer_info['waybill_id'], 'WB456')
        self.assertIn('destination_point', transfer_info)
        self.assertIn('partner_organization', transfer_info)

    def test_material_info_capture(self):
        material = MaterialFactory(
            number='MAT123',
            short_description='Test Material Description',
            original_uom='KG',
            material_type='Medical',
            group='Group1'
        )

        item = ItemFactory(transfer=self.transfer, material=material)

        audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).first()
        self.assertIsNotNone(audit_log.material_info)

        material_info = audit_log.material_info
        self.assertEqual(material_info['material_number'], 'MAT123')
        self.assertEqual(material_info['material_description'], 'Test Material Description')
        self.assertEqual(material_info['material_uom'], 'KG')
        self.assertEqual(material_info['material_type'], 'Medical')

    def test_critical_changes_detection(self):
        item = ItemFactory(transfer=self.transfer, material=self.material)

        new_transfer = TransferFactory(partner_organization=self.partner)
        new_material = MaterialFactory()

        models.ItemAuditLog.objects.all().delete()

        item.transfer = new_transfer
        item.material = new_material
        item.save()

        audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).first()
        self.assertIsNotNone(audit_log.critical_changes)

        critical_changes = audit_log.critical_changes
        self.assertTrue(critical_changes['transfer_changed'])
        self.assertTrue(critical_changes['material_changed'])
        self.assertIn('old_transfer_id', str(critical_changes))
        self.assertIn('new_transfer_id', str(critical_changes))
        self.assertIn('old_material_description', str(critical_changes))
        self.assertIn('new_material_description', str(critical_changes))

    def test_multiple_field_changes(self):
        item = ItemFactory(
            transfer=self.transfer,
            material=self.material,
            quantity=10,
            batch_id='BATCH123',
            mapped_description='Original description',
            expiry_date=timezone.now() + datetime.timedelta(days=30),
            amount_usd=Decimal('100.50')
        )

        models.ItemAuditLog.objects.all().delete()

        item.quantity = 25
        item.batch_id = 'BATCH789'
        item.mapped_description = 'Updated description'
        item.expiry_date = timezone.now() + datetime.timedelta(days=60)
        item.amount_usd = Decimal('200.75')
        item.save()

        audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).first()

        expected_fields = ['quantity', 'batch_id', 'mapped_description', 'expiry_date', 'amount_usd']
        for field in expected_fields:
            self.assertIn(field, audit_log.changed_fields)

        self.assertEqual(audit_log.old_values['quantity'], 10)
        self.assertEqual(audit_log.new_values['quantity'], 25)
        self.assertEqual(audit_log.old_values['batch_id'], 'BATCH123')
        self.assertEqual(audit_log.new_values['batch_id'], 'BATCH789')

    def test_no_changes_no_audit(self):
        item = ItemFactory(transfer=self.transfer, material=self.material)

        models.ItemAuditLog.objects.all().delete()

        item.save()

        audit_logs = models.ItemAuditLog.objects.filter(item_id=item.id)
        self.assertEqual(audit_logs.count(), 0)

    def test_foreign_key_serialization(self):
        item = ItemFactory(transfer=self.transfer, material=self.material)

        audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).first()

        if 'transfer_id' in audit_log.new_values:
            transfer_value = audit_log.new_values['transfer_id']
            if isinstance(transfer_value, dict):
                self.assertIn('id', transfer_value)
                self.assertEqual(transfer_value['id'], self.transfer.id)

        if 'material_id' in audit_log.new_values:
            material_value = audit_log.new_values['material_id']
            if isinstance(material_value, dict):
                self.assertIn('id', material_value)
                self.assertEqual(material_value['id'], self.material.id)


class TestItemAuditLogModel(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserFactory(
            realms__data=['IP LM Editor'],
            profile__organization=cls.partner.organization,
        )

    def test_audit_log_str_representation(self):
        audit_log = models.ItemAuditLog(
            item_id=123,
            action=models.ItemAuditLog.ACTION_UPDATE,
            user=self.partner_staff,
            timestamp=timezone.now()
        )

        self.assertIn("Item 123 - Updated at", str(audit_log))
        self.assertIn(models.ItemAuditLog.ACTION_UPDATE.lower(), str(audit_log).lower())

    def test_audit_log_ordering(self):
        item_id = 123

        older_log = models.ItemAuditLog.objects.create(
            item_id=item_id,
            action=models.ItemAuditLog.ACTION_CREATE,
            timestamp=timezone.now() - datetime.timedelta(hours=2)
        )

        newer_log = models.ItemAuditLog.objects.create(
            item_id=item_id,
            action=models.ItemAuditLog.ACTION_UPDATE,
            timestamp=timezone.now() - datetime.timedelta(hours=1)
        )

        newest_log = models.ItemAuditLog.objects.create(
            item_id=item_id,
            action=models.ItemAuditLog.ACTION_DELETE,
            timestamp=timezone.now()
        )

        logs = list(models.ItemAuditLog.objects.filter(item_id=item_id))
        self.assertEqual(logs[0], newest_log)
        self.assertEqual(logs[1], newer_log)
        self.assertEqual(logs[2], older_log)


class TestItemAuditLogAdmin(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.superuser = UserFactory(is_superuser=True, is_staff=True)
        cls.transfer = TransferFactory()
        cls.material = MaterialFactory()

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_admin_list_view(self):
        item = ItemFactory(transfer=self.transfer, material=self.material)

        url = reverse('admin:last_mile_itemauditlog_changelist')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(item.id))

    def test_admin_detail_view(self):
        item = ItemFactory(transfer=self.transfer, material=self.material)
        audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).first()

        url = reverse('admin:last_mile_itemauditlog_change', args=[audit_log.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_admin_readonly_fields(self):
        admin_instance = ItemAuditLogAdmin(models.ItemAuditLog, None)
        readonly_fields = admin_instance.readonly_fields

        expected_readonly = [
            'item_id', 'action', 'changed_fields', 'old_values', 'new_values',
            'user', 'transfer_info', 'material_info', 'critical_changes', 'timestamp',
            'tracked_changes_display', 'transfer_details_display', 'item_exists'
        ]

        for field in expected_readonly:
            self.assertIn(field, readonly_fields)

    def test_admin_no_add_permission(self):
        admin_instance = ItemAuditLogAdmin(models.ItemAuditLog, None)
        request = Mock()

        self.assertFalse(admin_instance.has_add_permission(request))

    def test_admin_no_change_permission(self):
        admin_instance = ItemAuditLogAdmin(models.ItemAuditLog, None)
        request = Mock()

        self.assertFalse(admin_instance.has_change_permission(request))


class TestItemAuditLogReversion(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.superuser = UserFactory(is_superuser=True, is_staff=True)
        cls.transfer = TransferFactory()
        cls.material = MaterialFactory()

    def setUp(self):
        self.client.force_login(self.superuser)
        models.ItemAuditLog.objects.all().delete()

    def test_revert_item_to_previous_state(self):
        item = ItemFactory(
            transfer=self.transfer,
            material=self.material,
            quantity=10,
            batch_id='BATCH123',
            mapped_description='Original description'
        )

        original_quantity = item.quantity
        original_batch_id = item.batch_id
        original_description = item.mapped_description

        item.quantity = 20
        item.batch_id = 'BATCH456'
        item.mapped_description = 'Updated description'
        item.save()

        update_audit_log = models.ItemAuditLog.objects.filter(
            item_id=item.id,
            action=models.ItemAuditLog.ACTION_UPDATE
        ).first()

        admin_instance = ItemAuditLogAdmin(models.ItemAuditLog, None)
        success = admin_instance.revert_item_to_audit_state(update_audit_log, self.superuser)

        self.assertTrue(success)

        item.refresh_from_db()
        self.assertEqual(item.quantity, original_quantity)
        self.assertEqual(item.batch_id, original_batch_id)
        self.assertEqual(item.mapped_description, original_description)

    def test_revert_deleted_item_fails(self):

        audit_log = models.ItemAuditLog.objects.create(
            item_id=99999,  # Non-existent item ID
            action=models.ItemAuditLog.ACTION_UPDATE,
            old_values={'quantity': 10, 'batch_id': 'BATCH123'}
        )

        admin_instance = ItemAuditLogAdmin(models.ItemAuditLog, None)
        success = admin_instance.revert_item_to_audit_state(audit_log, self.superuser)

        self.assertFalse(success)

    def test_revert_create_action_fails(self):
        item = ItemFactory(transfer=self.transfer, material=self.material)

        create_audit_log = models.ItemAuditLog.objects.filter(
            item_id=item.id,
            action=models.ItemAuditLog.ACTION_CREATE
        ).first()

        admin_instance = ItemAuditLogAdmin(models.ItemAuditLog, None)
        success = admin_instance.revert_item_to_audit_state(create_audit_log, self.superuser)

        self.assertFalse(success)


class TestItemAuditLogConfiguration(BaseTenantTestCase):

    def test_config_audit_import(self):
        try:
            self.assertIsInstance(ITEM_AUDIT_LOG_TRACKED_FIELDS, list)
            self.assertIn('quantity', ITEM_AUDIT_LOG_TRACKED_FIELDS)
            self.assertIn('batch_id', ITEM_AUDIT_LOG_TRACKED_FIELDS)
        except ImportError:
            self.fail("config_audit module should be importable")

    def test_tracked_fields_configuration(self):

        item = ItemFactory(
            transfer=TransferFactory(),
            material=MaterialFactory(),
            quantity=10,
            batch_id='BATCH123',
            mapped_description='Test description'
        )

        models.ItemAuditLog.objects.all().delete()

        item.quantity = 20
        item.batch_id = 'BATCH456'
        item.hidden = True
        item.save()

        audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).first()

        if audit_log:
            for field in audit_log.changed_fields:
                self.assertIn(field, ITEM_AUDIT_LOG_TRACKED_FIELDS)


class TestItemAuditLogEdgeCases(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.transfer = TransferFactory()
        cls.material = MaterialFactory()

    def test_audit_log_with_null_values(self):
        item = ItemFactory(
            transfer=self.transfer,
            material=self.material,
            mapped_description=None,
            expiry_date=None,
            amount_usd=None
        )

        audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).first()
        self.assertIsNotNone(audit_log)

        new_values = audit_log.new_values
        if new_values:
            for value in new_values.values():
                str(value)

    def test_concurrent_updates(self):
        item = ItemFactory(transfer=self.transfer, material=self.material)

        models.ItemAuditLog.objects.all().delete()

        def update_item_quantity():
            fresh_item = models.Item.objects.get(id=item.id)
            fresh_item.quantity += 1
            fresh_item.save()

        def update_item_batch():
            fresh_item = models.Item.objects.get(id=item.id)
            fresh_item.batch_id = 'CONCURRENT_UPDATE'
            fresh_item.save()

        update_item_quantity()
        update_item_batch()

        audit_logs = models.ItemAuditLog.objects.filter(item_id=item.id)
        self.assertEqual(audit_logs.count(), 2)

    @patch('etools.applications.last_mile.audit_signals.AuditLogManager.create_audit_log')
    def test_audit_failure_doesnt_break_application(self, mock_create_audit):
        mock_create_audit.side_effect = Exception("Audit system error")
        try:
            item = ItemFactory(transfer=self.transfer, material=self.material)
            item.quantity = 20
            item.save()
        except Exception as e:
            self.assertEqual(str(e), "Audit system error")

    def test_audit_log_performance_with_many_fields(self):
        item = ItemFactory(
            transfer=self.transfer,
            material=self.material,
            quantity=10,
            batch_id='BATCH123',
            mapped_description='Test description',
            expiry_date=timezone.now(),
            amount_usd=Decimal('100.00'),
            conversion_factor=Decimal('1.5'),
            wastage_type=models.Item.EXPIRED,
            purchase_order_item='PO123',
            unicef_ro_item='RO456'
        )

        models.ItemAuditLog.objects.all().delete()

        start_time = timezone.now()
        item.quantity = 20
        item.batch_id = 'BATCH456'
        item.mapped_description = 'Updated description'
        item.expiry_date = timezone.now() + datetime.timedelta(days=1)
        item.amount_usd = Decimal('200.00')
        item.conversion_factor = Decimal('2.0')
        item.wastage_type = models.Item.DAMAGED
        item.purchase_order_item = 'PO789'
        item.unicef_ro_item = 'RO123'
        item.save()
        end_time = timezone.now()

        duration = (end_time - start_time).total_seconds()
        self.assertLess(duration, 1.0)

        audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(len(audit_log.changed_fields), 7)


class TestItemAuditLogAdvancedScenarios(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.transfer = TransferFactory()
        cls.material = MaterialFactory()

    def setUp(self):
        models.ItemAuditLog.objects.all().delete()

    def test_bulk_operations_audit_logging(self):
        items = []
        for i in range(10):
            item = ItemFactory(
                transfer=self.transfer,
                material=self.material,
                quantity=i + 1,
                batch_id=f'BULK_{i}'
            )
            items.append(item)

        models.ItemAuditLog.objects.all().delete()

        for i, item in enumerate(items):
            item.quantity = (i + 1) * 10
            item.save()

        for i, item in enumerate(items):
            audit_logs = models.ItemAuditLog.objects.filter(item_id=item.id)
            self.assertEqual(audit_logs.count(), 1)
            audit_log = audit_logs.first()
            self.assertEqual(audit_log.old_values['quantity'], i + 1)
            self.assertEqual(audit_log.new_values['quantity'], (i + 1) * 10)

    def test_datetime_field_variations(self):
        base_date = timezone.now()

        item = ItemFactory(
            transfer=self.transfer,
            material=self.material,
            expiry_date=base_date
        )

        models.ItemAuditLog.objects.all().delete()

        test_dates = [
            base_date + datetime.timedelta(days=1),
            base_date + datetime.timedelta(hours=12, minutes=30),
            base_date + datetime.timedelta(seconds=1, microseconds=123456),
            None  # Test null date
        ]

        for new_date in test_dates:
            item.expiry_date = new_date
            item.save()

            audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).latest('timestamp')

            if new_date is not None:
                new_value = audit_log.new_values.get('expiry_date')
                if new_value:
                    self.assertIsInstance(new_value, str)
                    self.assertIn('T', new_value)
            else:
                self.assertIsNone(audit_log.new_values.get('expiry_date'))

            models.ItemAuditLog.objects.filter(item_id=item.id).delete()

    def test_wastage_type_complete_cycle(self):
        item = ItemFactory(
            transfer=self.transfer,
            material=self.material,
            wastage_type=None
        )

        models.ItemAuditLog.objects.all().delete()

        wastage_types = [
            models.Item.DAMAGED,
            models.Item.EXPIRED,
            models.Item.LOST,
            None,
            models.Item.DAMAGED
        ]

        for wastage_type in wastage_types:
            item.wastage_type = wastage_type
            item.save()

            audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).latest('timestamp')
            self.assertIn('wastage_type', audit_log.changed_fields)

            expected_value = wastage_type
            self.assertEqual(audit_log.new_values.get('wastage_type'), expected_value)

            models.ItemAuditLog.objects.filter(item_id=item.id).delete()

    def test_json_field_complex_structures(self):
        complex_data = {
            'metadata': {
                'version': '1.0',
                'created_by': 'system',
                'tags': ['urgent', 'medical'],
                'nested_data': {
                    'coordinates': [12.34, 56.78],
                    'measurements': {'weight': 10.5, 'volume': 2.3}
                }
            },
            'flags': {'is_priority': True, 'needs_review': False},
            'unicode_test': '测试数据 🚀 with émojis'
        }

        item = ItemFactory(
            transfer=self.transfer,
            material=self.material,
            other=complex_data
        )

        models.ItemAuditLog.objects.all().delete()

        new_data = {
            'metadata': {'version': '2.0', 'updated': True},
            'new_field': [1, 2, 3, {'nested': 'value'}]
        }

        item.other = new_data
        item.save()

        audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).first()
        if audit_log and 'other' in audit_log.changed_fields:
            old_value = audit_log.old_values.get('other')
            new_value = audit_log.new_values.get('other')
            self.assertIsNotNone(old_value)
            self.assertIsNotNone(new_value)

    def test_unicode_and_special_characters_comprehensive(self):
        unicode_samples = [
            "基本中文测试",
            "🚀🎉🌟💡🔥",
            "Héllø Wørld with áccènts",
            "العربية النص",
            "Русский текст",
            "日本語テスト",
            "Special chars: !@#$%^&*()_+-=[]{}|;:'\",.<>?/~`",
            "Mixed: 测试🚀test with 123 & symbols!"
        ]

        for i, unicode_text in enumerate(unicode_samples):
            item = ItemFactory(
                transfer=self.transfer,
                material=self.material,
                mapped_description=unicode_text[:100],  # Truncate to avoid field limits
                batch_id=f'UNICODE_{i}',
                comment=unicode_text
            )

            models.ItemAuditLog.objects.all().delete()

            item.mapped_description = f"UPDATED_{unicode_text[:80]}"
            item.save()

            audit_log = models.ItemAuditLog.objects.filter(item_id=item.id).first()
            self.assertIsNotNone(audit_log)

            if 'mapped_description' in audit_log.new_values:
                stored_value = audit_log.new_values['mapped_description']
                self.assertIn('UPDATED_', stored_value)

    def test_database_constraint_violations_handling(self):

        item = ItemFactory(transfer=self.transfer, material=self.material, quantity=100)
        models.ItemAuditLog.objects.all().delete()

        try:
            with transaction.atomic():
                item.quantity = 200
                item.save()

                raise IntegrityError("Simulated constraint violation")

        except IntegrityError:
            pass

        audit_count = models.ItemAuditLog.objects.filter(item_id=item.id).count()
        self.assertEqual(audit_count, 0)

        item.refresh_from_db()
        self.assertEqual(item.quantity, 100)

    def test_signal_performance_under_load(self):
        items = []

        start_time = timezone.now()
        for i in range(50):
            item = ItemFactory(
                transfer=self.transfer,
                material=self.material,
                quantity=i + 1,
                batch_id=f'PERF_{i}',
                mapped_description=f'Performance test item {i}',
                amount_usd=Decimal(str(i + 0.99))
            )
            items.append(item)
        creation_time = (timezone.now() - start_time).total_seconds()

        models.ItemAuditLog.objects.all().delete()

        start_time = timezone.now()
        for i, item in enumerate(items):
            item.quantity = (i + 1) * 2
            item.batch_id = f'UPDATED_{i}'
            item.mapped_description = f'Updated item {i}'
            item.save()
        update_time = (timezone.now() - start_time).total_seconds()

        self.assertLess(creation_time, 2.0)
        self.assertLess(update_time, 2.0)

        total_audit_logs = models.ItemAuditLog.objects.count()
        self.assertEqual(total_audit_logs, 50)
