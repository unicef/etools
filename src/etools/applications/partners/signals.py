from django.db import connection
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from etools.applications.partners.models import Intervention, InterventionSupplyItem
from etools.applications.partners.tasks import sync_partner_to_prp


@receiver(post_save, sender=Intervention)
def sync_pd_partner_to_prp(instance: Intervention, created: bool, **kwargs):
    if instance.submission_date and instance.tracker.has_changed('submission_date'):
        sync_partner_to_prp.delay(connection.tenant.name, instance.agreement.partner_id)


@receiver(post_delete, sender=InterventionSupplyItem)
def calc_totals_on_delete(instance, **kwargs):
    try:
        intervention = Intervention.objects.get(pk=instance.intervention.pk)
    except Intervention.DoesNotExist:
        pass
    else:
        intervention.planned_budget.calc_totals()
