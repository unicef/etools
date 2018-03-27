from __future__ import absolute_import, division, print_function, unicode_literals

from django.db.models.signals import post_save
from django.dispatch import receiver

from action_points.models import ActionPoint


@receiver(post_save, sender=ActionPoint)
def action_point_updated_receiver(instance, created, **kwargs):
    if created and instance.related_object is None:
        instance.send_email(instance.assigned_to, 'action_points/action_point/created_unlinked')
