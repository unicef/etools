import datetime

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from etools.applications.users.models import Realm
from etools.applications.users.tasks import sync_realms_to_prp


@receiver(post_save, sender=Realm)
def sync_realms_to_prp_on_update(instance: Realm, created: bool, **kwargs):
    transaction.on_commit(
        lambda:
            sync_realms_to_prp.apply_async(
                (instance.user_id, instance.modified),
                eta=instance.modified + datetime.timedelta(minutes=5)
            )
    )
