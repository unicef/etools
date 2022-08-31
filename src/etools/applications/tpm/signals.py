
from django.db import connection
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from etools.applications.tpm.models import ThirdPartyMonitor, TPMActionPoint, TPMVisit
from etools.applications.tpm.tpmpartners.models import TPMPartnerStaffMember
from etools.applications.users.models import Country, Realm


@receiver(post_delete, sender=TPMPartnerStaffMember)
def delete_user_receiver(instance, **kwargs):
    user = instance.user
    if not user.is_unicef_user():
        user.is_active = False
        user.save()


@receiver(post_save, sender=TPMActionPoint)
def action_point_updated_receiver(instance, created, **kwargs):
    if created:
        instance.send_email(instance.assigned_to, 'tpm/visit/action_point_assigned')
    else:
        if instance.tracker.has_changed('assigned_to'):
            instance.send_email(instance.assigned_to, 'tpm/visit/action_point_assigned')


@receiver(post_save, sender=TPMVisit)
def tpmvisit_save_receiver(instance, created, **kwargs):
    if instance.tpm_partner and (created or instance.tpm_partner_tracker.has_changed('tpm_partner')):
        country_in_use = Country.objects.get(schema_name=connection.schema_name)
        for staff in instance.tpm_partner.staff_members.exclude(user__profile__countries_available=country_in_use):
            Realm.objects.update_or_create(
                user=staff.user,
                country=country_in_use,
                organization=instance.tpm_partner.organization,
                group=ThirdPartyMonitor.as_group()
            )
