import logging

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from etools.applications.last_mile.models import Item, ItemAuditLog
from etools.applications.last_mile.services.audit_log_service import AuditLogService
from etools.applications.last_mile.utils.config_audit import ITEM_AUDIT_LOG_TRACKED_FIELDS
from etools.applications.last_mile.utils.user_detection import get_current_user

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Item)
def store_original_item(sender, instance, **kwargs):
    if not AuditLogService.should_audit(instance):
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
    if not AuditLogService.should_audit(instance, user):
        return

    if created:
        new_values = {}
        for field in ITEM_AUDIT_LOG_TRACKED_FIELDS:
            if hasattr(instance, field):
                value = getattr(instance, field)
                new_values[field] = AuditLogService.serialize_field_value(instance, field, value)

        AuditLogService.create_audit_log(
            item_id=instance.id,
            action=ItemAuditLog.ACTION_CREATE,
            new_values=new_values,
            user=user,
            instance=instance
        )
    else:
        original = getattr(instance, '_original', None)
        if original:
            changed_fields = AuditLogService.get_changed_fields(original, instance)

            if changed_fields:
                old_values = {}
                new_values = {}

                for field, old_value in changed_fields.items():
                    old_values[field] = AuditLogService.serialize_field_value(original, field, old_value)
                    new_value = getattr(instance, field)
                    new_values[field] = AuditLogService.serialize_field_value(instance, field, new_value)

                action = (ItemAuditLog.ACTION_SOFT_DELETE if hasattr(instance, 'hidden') and instance.hidden else ItemAuditLog.ACTION_UPDATE)

                AuditLogService.create_audit_log(
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

    if not AuditLogService.should_audit(instance, user):
        return

    old_values = {}
    for field in ITEM_AUDIT_LOG_TRACKED_FIELDS:
        if hasattr(instance, field):
            value = getattr(instance, field)
            old_values[field] = AuditLogService.serialize_field_value(instance, field, value)

    action = (ItemAuditLog.ACTION_SOFT_DELETE if hasattr(instance, 'hidden') and instance.hidden else ItemAuditLog.ACTION_DELETE)

    AuditLogService.create_audit_log(
        item_id=instance.id,
        action=action,
        old_values=old_values,
        user=user,
        instance=instance,
    )
