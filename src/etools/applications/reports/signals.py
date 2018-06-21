from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from etools.applications.reports.models import AppliedIndicator


@receiver(m2m_changed, sender=AppliedIndicator.locations.through)
def clear_intervention_locations_caches(sender, instance, action, reverse, pk_set, *args, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        instance.lower_result.result_link.intervention.clear_caches()
