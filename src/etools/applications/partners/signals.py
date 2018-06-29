from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from etools.applications.partners.models import Intervention


@receiver(m2m_changed, sender=Intervention.flat_locations.through)
def clear_intervention_locations_caches(sender, instance, action, reverse, pk_set, *args, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        instance.intervention_locations(reset=True)


@receiver(m2m_changed, sender=Intervention.sections.through)
def clear_intervention_section_caches(sender, instance, action, reverse, pk_set, *args, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        instance.flagged_sections(reset=True)
