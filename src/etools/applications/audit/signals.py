
from django.db import connection
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from etools.applications.audit.models import Auditor, Engagement, EngagementActionPoint
from etools.applications.audit.purchase_order.models import AuditorStaffMember
from etools.applications.users.models import Country


@receiver(post_save, sender=AuditorStaffMember)
def create_user_receiver(instance, created, **kwargs):
    if created:
        instance.user.groups.add(Auditor.as_group())


@receiver(m2m_changed, sender=Engagement.staff_members.through)
def staff_member_changed(sender, instance, action, reverse, pk_set, *args, **kwargs):
    if action == 'post_add':
        new_members = AuditorStaffMember.objects.filter(id__in=pk_set).select_related('user', 'user__profile')

        engagement = Engagement.objects.get_subclass(id=instance.id)
        for member in new_members:
            member.send_user_appointed_email(engagement)

        country = Country.objects.get(schema_name=connection.schema_name)
        for member in new_members:
            member.user.profile.countries_available.add(country)


@receiver(post_delete, sender=AuditorStaffMember)
def delete_user_receiver(instance, **kwargs):
    user = instance.user
    user.is_active = False
    user.save()


@receiver(post_save, sender=EngagementActionPoint)
def action_point_updated_receiver(instance, created, **kwargs):
    if created:
        instance.notify_person_responsible('audit/engagement/action_point_assigned')
