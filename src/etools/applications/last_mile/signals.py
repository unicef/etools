import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from etools.applications.last_mile.models import Item
from etools.applications.last_mile.serializers import ItemSerializer

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Item)
def log_transfer(sender, instance, **kwargs):
    transfer = getattr(instance, "transfer", None)
    if not transfer:
        logger.warning(f"Item has no transfer : {instance}")
        return  # No transfer available, exit early

    if transfer.status == transfer.PENDING and instance.quantity > 0:
        item_exists = any(item['id'] == instance.pk for item in transfer.initial_items or [])

        if not item_exists:
            transfer.initial_items = (transfer.initial_items or []) + [ItemSerializer(instance).data]
            transfer.save(update_fields=["initial_items"])

    transfer_origin_pk = getattr(transfer.origin_transfer, "pk", None)
    original_transfer = getattr(instance, "origin_transfer", None)
    original_transfer_pk = getattr(original_transfer, "pk", None)

    try:
        transfer.add_transfer_history(
            origin_transfer_pk=transfer_origin_pk, original_transfer_pk=original_transfer_pk
        )
    except Exception:
        logger.exception("Error adding transfer history")
