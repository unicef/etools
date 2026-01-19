import datetime

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from etools.applications.last_mile.services.permissions_service import LMSMPermissionsService
from etools.applications.users.models import Realm
from etools.applications.users.tasks import sync_realms_to_prp


@receiver(post_save, sender=Realm)
def sync_realms_to_prp_on_update(instance: Realm, created: bool, **kwargs):
    # Create an instance of the permissions service
    permissions_service = LMSMPermissionsService()

    # Check if this is an LMSM admin group and handle permissions (both activation and deactivation)
    if permissions_service.is_lmsm_admin_group(instance.group.name):
        permissions_service.handle_realm_save_permissions(instance, created)
        return

    if instance.user.is_unicef_user():
        # only external users are allowed to be synced to prp
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
    # Create an instance of the permissions service
    permissions_service = LMSMPermissionsService()

    # Check if this is an LMSM admin group and handle permissions and not sync to PRP
    if permissions_service.is_lmsm_admin_group(instance.group.name):
        permissions_service.handle_realm_deletion_permissions(instance)
        return

    if instance.user.is_unicef_user():
        # only external users are allowed to be synced to prp
        return

    now = timezone.now()
    transaction.on_commit(
        lambda:
            sync_realms_to_prp.apply_async(
                (instance.user_id, now.timestamp()),
                eta=now + datetime.timedelta(minutes=settings.PRP_USER_SYNC_DELAY)
            )
    )
