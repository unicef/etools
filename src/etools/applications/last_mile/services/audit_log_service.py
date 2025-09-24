import logging

from django.db import transaction

from etools.applications.core.middleware import get_current_user
from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.last_mile.models import AuditConfiguration, Item, ItemAuditLog

logger = logging.getLogger(__name__)


class AuditLogService:

    def handle_pre_save(self, instance, **kwargs):
        if not self.should_audit(instance):
            return

        if instance.pk:
            try:
                instance._original = Item.objects.get(pk=instance.pk)
            except Item.DoesNotExist:
                instance._original = None
        else:
            instance._original = None

    def handle_post_save(self, instance, created, **kwargs):
        user = get_current_user()
        if not self.should_audit(instance, user):
            return

        if created:
            self._handle_item_creation(instance, user)
        else:
            self._handle_item_update(instance, user)

    def handle_post_delete(self, instance, **kwargs):
        user = get_current_user()
        if not self.should_audit(instance, user):
            return

        self._handle_item_deletion(instance, user)

    def _handle_item_creation(self, instance, user):
        config = AuditConfiguration.get_active_config()
        tracked_fields = config.tracked_fields if config else []

        new_values = {}
        for field in tracked_fields:
            if hasattr(instance, field):
                value = getattr(instance, field)
                new_values[field] = self.serialize_field_value(instance, field, value)

        self.create_audit_log(
            item_id=instance.id,
            action=ItemAuditLog.ACTION_CREATE,
            new_values=new_values,
            user=user,
            instance=instance
        )

    def _handle_item_update(self, instance, user):
        original = getattr(instance, '_original', None)
        if not original:
            return

        changed_fields = self.get_changed_fields(original, instance)
        if not changed_fields:
            return

        old_values = {}
        new_values = {}

        for field, old_value in changed_fields.items():
            old_values[field] = self.serialize_field_value(original, field, old_value)
            new_value = getattr(instance, field)
            new_values[field] = self.serialize_field_value(instance, field, new_value)

        action = (ItemAuditLog.ACTION_SOFT_DELETE if hasattr(instance, 'hidden') and instance.hidden else ItemAuditLog.ACTION_UPDATE)

        self.create_audit_log(
            item_id=instance.id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            user=user,
            instance=instance,
            original_instance=original
        )

    def _handle_item_deletion(self, instance, user):
        config = AuditConfiguration.get_active_config()
        tracked_fields = config.tracked_fields if config else []

        old_values = {}
        for field in tracked_fields:
            if hasattr(instance, field):
                value = getattr(instance, field)
                old_values[field] = self.serialize_field_value(instance, field, value)

        action = (ItemAuditLog.ACTION_SOFT_DELETE if hasattr(instance, 'hidden') and instance.hidden else ItemAuditLog.ACTION_DELETE)

        self.create_audit_log(
            item_id=instance.id,
            action=action,
            old_values=old_values,
            user=user,
            instance=instance,
        )

    def should_audit(self, instance, user=None):
        if not tenant_switch_is_active("lmsm_item_audit_logs"):
            return False
        config = AuditConfiguration.get_active_config()
        if not config or not config.is_enabled:
            return False

        if user and user.id in config.excluded_user_ids:
            return False

        if user and not config.track_system_users and (user.is_staff or user.is_superuser):
            return False

        return True

    def get_changed_fields(self, old_instance, new_instance):
        config = AuditConfiguration.get_active_config()
        if not config:
            return {}

        tracked_fields = config.tracked_fields or []

        if not old_instance:
            return {
                field: None for field in tracked_fields
                if hasattr(new_instance, field)
            }

        changed_fields = {}
        for field in tracked_fields:
            if hasattr(old_instance, field) and hasattr(new_instance, field):
                old_value = getattr(old_instance, field)
                new_value = getattr(new_instance, field)
                if old_value != new_value:
                    changed_fields[field] = old_value

        return changed_fields

    def serialize_field_value(self, instance, field_name, value):
        if value is None:
            return None

        config = AuditConfiguration.get_active_config()
        fk_fields = config.fk_field_mappings if config else {}

        if field_name in fk_fields:
            if hasattr(instance, fk_fields[field_name]):
                related_obj = getattr(instance, fk_fields[field_name])
                if related_obj:
                    return {
                        'id': value,
                        'str': str(related_obj)
                    }
            return {'id': value, 'str': None}

        if hasattr(value, 'isoformat'):
            return value.isoformat()

        if hasattr(value, '__float__'):
            return float(value)

        return str(value)

    def get_transfer_info(self, instance):
        transfer_info = {}

        if hasattr(instance, 'transfer') and instance.transfer:
            transfer = instance.transfer
            transfer_info['transfer_id'] = transfer.id
            transfer_info['transfer_name'] = transfer.name or f"Transfer #{transfer.id}"
            transfer_info['transfer_type'] = transfer.transfer_type
            transfer_info['transfer_status'] = transfer.status
            transfer_info['unicef_release_order'] = transfer.unicef_release_order
            transfer_info['waybill_id'] = transfer.waybill_id

            if transfer.origin_point:
                transfer_info['origin_point'] = {
                    'id': transfer.origin_point.id,
                    'name': transfer.origin_point.name,
                    'p_code': transfer.origin_point.p_code
                }

            if transfer.destination_point:
                transfer_info['destination_point'] = {
                    'id': transfer.destination_point.id,
                    'name': transfer.destination_point.name,
                    'p_code': transfer.destination_point.p_code
                }

            if transfer.partner_organization:
                transfer_info['partner_organization'] = {
                    'id': transfer.partner_organization.id,
                    'name': transfer.partner_organization.name
                }

        return transfer_info if transfer_info else None

    def get_material_info(self, instance):
        material_info = {}

        if hasattr(instance, 'material') and instance.material:
            material = instance.material
            material_info['material_id'] = material.id
            material_info['material_number'] = material.number
            material_info['material_description'] = material.short_description
            material_info['material_uom'] = material.original_uom
            material_info['material_group'] = material.group
            material_info['material_type'] = material.material_type

        return material_info if material_info else None

    def detect_critical_changes(self, old_instance, new_instance):
        critical_changes = {}

        if not old_instance:
            return critical_changes

        old_transfer_id = getattr(old_instance, 'transfer_id', None)
        new_transfer_id = getattr(new_instance, 'transfer_id', None)
        if old_transfer_id != new_transfer_id:
            critical_changes['transfer_changed'] = {
                'old_transfer_id': old_transfer_id,
                'new_transfer_id': new_transfer_id,
                'old_transfer_name': old_instance.transfer.name if old_instance.transfer else None,
                'new_transfer_name': new_instance.transfer.name if new_instance.transfer else None
            }

        old_material_id = getattr(old_instance, 'material_id', None)
        new_material_id = getattr(new_instance, 'material_id', None)
        if old_material_id != new_material_id:
            critical_changes['material_changed'] = {
                'old_material_id': old_material_id,
                'new_material_id': new_material_id,
                'old_material_number': old_instance.material.number if old_instance.material else None,
                'new_material_number': new_instance.material.number if new_instance.material else None,
                'old_material_description': old_instance.material.short_description if old_instance.material else None,
                'new_material_description': new_instance.material.short_description if new_instance.material else None
            }

        return critical_changes if critical_changes else None

    def create_audit_log(self, item_id, action, old_values=None, new_values=None, changed_fields=None, user=None, instance=None, original_instance=None):
        try:
            with transaction.atomic():
                self.cleanup_old_entries(item_id)

                transfer_info = None
                material_info = None
                critical_changes = None

                if instance:
                    transfer_info = self.get_transfer_info(instance)
                    material_info = self.get_material_info(instance)

                    if action == ItemAuditLog.ACTION_UPDATE and original_instance:
                        critical_changes = self.detect_critical_changes(original_instance, instance)

                ItemAuditLog.objects.create(
                    item_id=item_id,
                    action=action,
                    changed_fields=list(changed_fields.keys()) if changed_fields else None,
                    old_values=old_values,
                    new_values=new_values,
                    user=user,
                    transfer_info=transfer_info,
                    material_info=material_info,
                    critical_changes=critical_changes
                )
        except Exception as e:
            logger.error(f"Failed to create audit log for item {item_id}: {e}")

    def cleanup_old_entries(self, item_id):
        config = AuditConfiguration.get_active_config()
        if not config or config.max_entries_per_item <= 0:
            return

        count = ItemAuditLog.objects.filter(item_id=item_id).count()
        if count >= config.max_entries_per_item:
            entries_to_delete = count - config.max_entries_per_item + 1
            old_entries = ItemAuditLog.objects.filter(item_id=item_id).order_by('created')[:entries_to_delete]
            old_entry_ids = list(old_entries.values_list('id', flat=True))
            ItemAuditLog.objects.filter(id__in=old_entry_ids).delete()
