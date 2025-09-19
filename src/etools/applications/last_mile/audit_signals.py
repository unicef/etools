import inspect
import threading

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from etools.applications.last_mile.config_audit import (
    ITEM_AUDIT_LOG_ENABLED,
    ITEM_AUDIT_LOG_EXCLUDE_USERS,
    ITEM_AUDIT_LOG_FK_FIELDS,
    ITEM_AUDIT_LOG_MAX_ENTRIES_PER_ITEM,
    ITEM_AUDIT_LOG_SYSTEM_USERS,
    ITEM_AUDIT_LOG_TRACKED_FIELDS,
)
from etools.applications.last_mile.models import Item, ItemAuditLog


def get_current_user_from_stack():

    frame = inspect.currentframe()
    try:
        while frame:
            local_vars = frame.f_locals

            if 'self' in local_vars:
                obj = local_vars['self']
                if hasattr(obj, 'request'):
                    request = obj.request
                    if hasattr(request, 'user') and request.user.is_authenticated:
                        return request.user

            if 'request' in local_vars:
                request = local_vars['request']
                if hasattr(request, 'user') and request.user.is_authenticated:
                    return request.user

            if 'user' in local_vars:
                user = local_vars['user']
                if hasattr(user, 'is_authenticated') and user.is_authenticated:
                    return user

            frame = frame.f_back
    finally:
        del frame

    return None


def get_current_user():

    user = get_current_user_from_stack()
    if user:
        return user

    return None


class AuditLogManager:

    @staticmethod
    def should_audit(instance, user=None):
        if not ITEM_AUDIT_LOG_ENABLED:
            return False

        if user and user.id in ITEM_AUDIT_LOG_EXCLUDE_USERS:
            return False

        if user and not ITEM_AUDIT_LOG_SYSTEM_USERS and (user.is_staff or user.is_superuser):
            return False

        return True

    @staticmethod
    def get_changed_fields(old_instance, new_instance):
        if not old_instance:
            return {
                field: None for field in ITEM_AUDIT_LOG_TRACKED_FIELDS
                if hasattr(new_instance, field)
            }

        changed_fields = {}
        for field in ITEM_AUDIT_LOG_TRACKED_FIELDS:
            if hasattr(old_instance, field) and hasattr(new_instance, field):
                old_value = getattr(old_instance, field)
                new_value = getattr(new_instance, field)
                if old_value != new_value:
                    changed_fields[field] = old_value

        return changed_fields

    @staticmethod
    def serialize_field_value(instance, field_name, value):
        if value is None:
            return None

        if field_name in ITEM_AUDIT_LOG_FK_FIELDS:
            if hasattr(instance, ITEM_AUDIT_LOG_FK_FIELDS[field_name]):
                related_obj = getattr(instance, ITEM_AUDIT_LOG_FK_FIELDS[field_name])
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

    @staticmethod
    def get_transfer_info(instance):
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

    @staticmethod
    def get_material_info(instance):
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

    @staticmethod
    def detect_critical_changes(old_instance, new_instance):
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

    @staticmethod
    def create_audit_log(item_id, action, old_values=None, new_values=None, changed_fields=None, user=None, instance=None, original_instance=None):
        try:
            with transaction.atomic():
                AuditLogManager.cleanup_old_entries(item_id)

                transfer_info = None
                material_info = None
                critical_changes = None

                if instance:
                    transfer_info = AuditLogManager.get_transfer_info(instance)
                    material_info = AuditLogManager.get_material_info(instance)

                    if action == ItemAuditLog.ACTION_UPDATE and original_instance:
                        critical_changes = AuditLogManager.detect_critical_changes(original_instance, instance)

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
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create audit log for item {item_id}: {e}")

    @staticmethod
    def cleanup_old_entries(item_id):
        if ITEM_AUDIT_LOG_MAX_ENTRIES_PER_ITEM <= 0:
            return

        count = ItemAuditLog.objects.filter(item_id=item_id).count()
        if count >= ITEM_AUDIT_LOG_MAX_ENTRIES_PER_ITEM:
            entries_to_delete = count - ITEM_AUDIT_LOG_MAX_ENTRIES_PER_ITEM + 1
            old_entries = ItemAuditLog.objects.filter(item_id=item_id).order_by('timestamp')[:entries_to_delete]
            old_entry_ids = list(old_entries.values_list('id', flat=True))
            ItemAuditLog.objects.filter(id__in=old_entry_ids).delete()


@receiver(pre_save, sender=Item)
def store_original_item(sender, instance, **kwargs):
    if not AuditLogManager.should_audit(instance):
        return

    if instance.pk:
        try:
            instance._original = Item.objects.get(pk=instance.pk)
        except Item.DoesNotExist:
            instance._original = None
    else:
        instance._original = None


@receiver(post_save, sender=Item)
def audit_item_save(sender, instance, created, **kwargs):
    user = get_current_user()
    if not AuditLogManager.should_audit(instance, user):
        return

    if created:
        new_values = {}
        for field in ITEM_AUDIT_LOG_TRACKED_FIELDS:
            if hasattr(instance, field):
                value = getattr(instance, field)
                new_values[field] = AuditLogManager.serialize_field_value(instance, field, value)

        AuditLogManager.create_audit_log(
            item_id=instance.id,
            action=ItemAuditLog.ACTION_CREATE,
            new_values=new_values,
            user=user,
            instance=instance
        )
    else:
        original = getattr(instance, '_original', None)
        if original:
            changed_fields = AuditLogManager.get_changed_fields(original, instance)

            if changed_fields:
                old_values = {}
                new_values = {}

                for field, old_value in changed_fields.items():
                    old_values[field] = AuditLogManager.serialize_field_value(original, field, old_value)
                    new_value = getattr(instance, field)
                    new_values[field] = AuditLogManager.serialize_field_value(instance, field, new_value)
                action = ItemAuditLog.ACTION_SOFT_DELETE if hasattr(instance, 'hidden') and instance.hidden else ItemAuditLog.ACTION_UPDATE
                AuditLogManager.create_audit_log(
                    item_id=instance.id,
                    action=action,
                    old_values=old_values,
                    new_values=new_values,
                    changed_fields=changed_fields,
                    user=user,
                    instance=instance,
                    original_instance=original
                )


@receiver(post_delete, sender=Item)
def audit_item_delete(sender, instance, **kwargs):
    user = get_current_user()

    if not AuditLogManager.should_audit(instance, user):
        return

    old_values = {}
    for field in ITEM_AUDIT_LOG_TRACKED_FIELDS:
        if hasattr(instance, field):
            value = getattr(instance, field)
            old_values[field] = AuditLogManager.serialize_field_value(instance, field, value)

    action = ItemAuditLog.ACTION_SOFT_DELETE if hasattr(instance, 'hidden') and instance.hidden else ItemAuditLog.ACTION_DELETE

    AuditLogManager.create_audit_log(
        item_id=instance.id,
        action=action,
        old_values=old_values,
        user=user,
        instance=instance,
    )


_audit_context = threading.local()


def set_audit_user(user):
    _audit_context.user = user


def get_audit_user():
    return getattr(_audit_context, 'user', None)


class audit_context:

    def __init__(self, user):
        self.user = user
        self.previous_user = None

    def __enter__(self):
        self.previous_user = get_audit_user()
        set_audit_user(self.user)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_audit_user(self.previous_user)
