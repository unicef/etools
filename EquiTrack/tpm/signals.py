from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import connection
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from firms.utils import send_invite_email
from users.models import Country
from tpm.models import ThirdPartyMonitor, TPMActionPoint, TPMVisit
from tpm.tpmpartners.models import TPMPartnerStaffMember


@receiver(post_save, sender=TPMPartnerStaffMember)
def create_user_receiver(instance, created, **kwargs):
    if created:
        instance.user.groups.add(ThirdPartyMonitor.as_group())

        send_invite_email(instance)


@receiver(post_delete, sender=TPMPartnerStaffMember)
def delete_user_receiver(instance, **kwargs):
    instance.user.delete()


@receiver(post_save, sender=TPMActionPoint)
def action_point_updated_receiver(instance, created, **kwargs):
    if created:
        instance.notify_person_responsible('tpm/visit/action_point_assigned')


@receiver(post_save, sender=TPMVisit)
def tpmvisit_save_receiver(instance, created, **kwargs):
    if instance.tpm_partner and (created or instance.tpm_partner_tracker.has_changed('tpm_partner')):
        country_in_use = Country.objects.get(schema_name=connection.schema_name)
        for staff in instance.tpm_partner.staff_members.exclude(user__profile__countries_available=country_in_use):
            staff.user.profile.countries_available.add(country_in_use)
