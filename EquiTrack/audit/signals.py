from __future__ import absolute_import, division, print_function, unicode_literals

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from audit.models import Auditor, AuditorStaffMember, Engagement, EngagementActionPoint


@receiver(post_save, sender=AuditorStaffMember)
def create_user_receiver(instance, created, **kwargs):
    if created:
        instance.user.groups.add(Auditor.as_group())

        instance.send_invite_email()


@receiver(m2m_changed, sender=Engagement.staff_members.through)
def staff_member_changed(sender, instance, action, reverse, pk_set, *args, **kwargs):
    if action == 'post_add':
        new_members = AuditorStaffMember.objects.filter(id__in=pk_set)
        for member in new_members:
            member.send_user_appointed_email(Engagement.objects.get_subclass(id=instance.id))


@receiver(post_delete, sender=AuditorStaffMember)
def delete_user_receiver(instance, **kwargs):
    instance.user.delete()


@receiver(post_save, sender=EngagementActionPoint)
def action_point_updated_receiver(instance, created, **kwargs):
    if created:
        instance.notify_person_responsible('audit/engagement/action_point_assigned')
