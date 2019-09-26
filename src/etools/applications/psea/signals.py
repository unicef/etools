from django.db.models.signals import post_save
from django.dispatch import receiver

from etools.applications.psea.models import AssessmentActionPoint


@receiver(post_save, sender=AssessmentActionPoint)
def action_point_updated_receiver(instance, created, **kwargs):
    if created:
        instance.send_email(
            instance.assigned_to,
            'audit/engagement/action_point_assigned',
            cc=[instance.assigned_by.email],
        )
    else:
        if instance.tracker.has_changed('assigned_to'):
            instance.send_email(
                instance.assigned_to,
                'audit/engagement/action_point_assigned',
            )
