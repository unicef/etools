import datetime

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from etools.applications.users.models import Realm, Permission
from etools.applications.users.tasks import sync_realms_to_prp

LMSM_CO_ADMIN = "IP LMSM CO Admin"
LMSM_HQ_ADMIN = "IP LMSM HQ Admin"

@receiver(post_save, sender=Realm)
def sync_realms_to_prp_on_update(instance: Realm, created: bool, **kwargs):
    if instance.user.is_unicef_user():
        # only external users are allowed to be synced to prp
        return
    # Lastmile realms not synced to prp
    if instance.group.name in ["IP LM Editor", "LMSMApi", LMSM_CO_ADMIN, LMSM_HQ_ADMIN]:
        if instance.group.name == LMSM_CO_ADMIN:
            pass
        if instance.group.name == LMSM_HQ_ADMIN:
            pass
        return
    transaction.on_commit(
        lambda:
            sync_realms_to_prp.apply_async(
                (instance.user_id, instance.modified.timestamp()),
                eta=instance.modified + datetime.timedelta(minutes=settings.PRP_USER_SYNC_DELAY)
            )
    )


@receiver(post_delete, sender=Realm)
def sync_realms_to_prp_on_delete(instance: Realm, **kwargs):
    if instance.user.is_unicef_user():
        # only external users are allowed to be synced to prp
        return

    # Lastmile realms not synced to prp
    if instance.group.name in ["IP LM Editor", "LMSMApi", LMSM_CO_ADMIN, LMSM_HQ_ADMIN]:
        if instance.group.name == LMSM_CO_ADMIN:
            pass
        if instance.group.name == LMSM_HQ_ADMIN:
            pass
        return

    now = timezone.now()
    transaction.on_commit(
        lambda:
            sync_realms_to_prp.apply_async(
                (instance.user_id, now.timestamp()),
                eta=now + datetime.timedelta(minutes=settings.PRP_USER_SYNC_DELAY)
            )
    )
