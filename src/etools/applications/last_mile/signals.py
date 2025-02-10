from django.db.models.signals import post_save
from django.dispatch import receiver

from etools.applications.last_mile.models import Item


@receiver(post_save, sender=Item)
def log_transfer(sender, instance, **kwargs):
    transfer = getattr(instance, "transfer", None)
    if not transfer:
        return  # No transfer available, exit early

    transfer_origin_pk = getattr(transfer.origin_transfer, "pk", None)
    original_transfer = getattr(instance, "origin_transfer", None)
    original_transfer_pk = getattr(original_transfer, "pk", None)

    try:
        history = transfer.add_transfer_history(
            origin_transfer_pk=transfer_origin_pk, transfer_pk=transfer.pk, original_transfer_pk=original_transfer_pk
        )
        transfer.set_transfer_history(history, save=True)
    except Exception:
        pass
