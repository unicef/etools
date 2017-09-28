from __future__ import unicode_literals

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import TPMPartnerStaffMember, ThirdPartyMonitor, TPMActionPoint


@receiver(post_save, sender=TPMPartnerStaffMember)
def create_user_receiver(instance, created, **kwargs):
    if created:
        instance.user.groups.add(ThirdPartyMonitor.as_group())

        instance.send_invite_email()


@receiver(post_delete, sender=TPMPartnerStaffMember)
def delete_user_receiver(instance, **kwargs):
    instance.user.delete()


@receiver(post_save, sender=TPMActionPoint)
def action_point_updated_receiver(instance, created, **kwargs):
    if created:
        instance.notify_person_responsible('tpm/visit/action_point_assigned')
