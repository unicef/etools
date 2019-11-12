from django.db.models.signals import post_save
from django.dispatch import receiver

from etools.applications.action_points.models import ActionPoint
from etools.applications.t2f.models import TravelActivity


@receiver(post_save, sender=ActionPoint)
def action_point_updated_receiver(instance, created, **kwargs):

    relevant_ap_instance = False
    if isinstance(instance.related_object, TravelActivity):
        email_template = 't2f/travel_activity/action_point_assigned'
        relevant_ap_instance = True
    elif instance.related_object is None:
        email_template = 'action_points/action_point/assigned'
        relevant_ap_instance = True

    if relevant_ap_instance:
        if created:
            instance.send_email(instance.assigned_to, email_template, cc=[instance.assigned_by.email])
        elif not instance.tracker.has_changed('reference_number'):
            if instance.tracker.has_changed('assigned_to'):
                instance.send_email(instance.assigned_to, email_template)
