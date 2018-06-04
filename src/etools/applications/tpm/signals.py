
from django.db import connection
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from etools.applications.tpm.models import ThirdPartyMonitor, TPMActionPoint, TPMVisit
from etools.applications.tpm.tpmpartners.models import TPMPartnerStaffMember
from etools.applications.users.models import Country


@receiver(post_save, sender=TPMPartnerStaffMember)
def create_user_receiver(instance, created, **kwargs):
    if created:
        instance.user.groups.add(ThirdPartyMonitor.as_group())


@receiver(post_delete, sender=TPMPartnerStaffMember)
def delete_user_receiver(instance, **kwargs):
    user = instance.user
    user.is_active = False
    user.save()


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
