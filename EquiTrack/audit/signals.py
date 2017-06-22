from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver

from audit.models import AuditorStaffMember, Auditor, Engagement


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
            member.send_user_appointed_email(instance)


@receiver(post_delete, sender=AuditorStaffMember)
def delete_user_receiver(instance, **kwargs):
    instance.user.delete()
