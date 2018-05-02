from __future__ import absolute_import, division, print_function, unicode_literals

from django.db.models.signals import post_save
from django.dispatch import receiver

from action_points.models import ActionPoint


@receiver(post_save, sender=ActionPoint)
def action_point_updated_receiver(instance, created, **kwargs):
    if created:
        if instance.related_module is None:
            instance.send_email(instance.assigned_to, 'action_points/action_point/assigned')
    else:
        if instance.tracker.has_changed('assigned_to'):
            instance.send_email(instance.assigned_to, 'action_points/action_point/assigned')
