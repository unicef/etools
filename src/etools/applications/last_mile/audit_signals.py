import logging

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from etools.applications.last_mile.models import Item
from etools.applications.last_mile.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Item)
def store_original_item(sender, instance, **kwargs):
    audit_service = AuditLogService()
    audit_service.handle_pre_save(instance, **kwargs)


@receiver(post_save, sender=Item)
def audit_item_save(sender, instance, created, **kwargs):
    audit_service = AuditLogService()
    audit_service.handle_post_save(instance, created, **kwargs)


@receiver(post_delete, sender=Item)
def audit_item_delete(sender, instance, **kwargs):
    audit_service = AuditLogService()
    audit_service.handle_post_delete(instance, **kwargs)
