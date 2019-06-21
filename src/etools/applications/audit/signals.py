from django.db import connection
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from etools.applications.audit.models import Engagement, EngagementActionPoint
from etools.applications.audit.purchase_order.models import AuditorStaffMember
from etools.applications.users.models import Country


@receiver(m2m_changed, sender=Engagement.staff_members.through)
def staff_member_changed(sender, instance, action, reverse, pk_set, *args, **kwargs):
    if action == 'post_add':
        new_members = AuditorStaffMember.objects.filter(id__in=pk_set).select_related('user', 'user__profile')

        engagement = instance.get_subclass()
        for member in new_members:
            member.send_user_appointed_email(engagement)

        country = Country.objects.get(schema_name=connection.schema_name)
        for member in new_members:
            member.user.profile.countries_available.add(country)


@receiver(post_save, sender=EngagementActionPoint)
def action_point_updated_receiver(instance, created, **kwargs):
    if created:
        instance.send_email(instance.assigned_to, 'audit/engagement/action_point_assigned',
                            cc=[instance.assigned_by.email])
    elif not instance.tracker.has_changed('reference_number'):
        if instance.tracker.has_changed('assigned_to'):
            instance.send_email(instance.assigned_to, 'audit/engagement/action_point_assigned')
