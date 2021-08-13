from django.db import connection
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from etools.applications.partners.models import (
    Intervention,
    InterventionBudget,
    InterventionReview,
    InterventionSupplyItem,
    PRCOfficerInterventionReview,
)
from etools.applications.partners.tasks import sync_partner_to_prp


@receiver(post_save, sender=Intervention)
def sync_pd_partner_to_prp(instance: Intervention, created: bool, **kwargs):
    if instance.date_sent_to_partner and instance.tracker.has_changed('date_sent_to_partner'):
        sync_partner_to_prp.delay(connection.tenant.name, instance.agreement.partner_id)


@receiver(post_delete, sender=InterventionSupplyItem)
def calc_totals_on_delete(instance, **kwargs):
    try:
        intervention = Intervention.objects.get(pk=instance.intervention.pk)
    except Intervention.DoesNotExist:
        pass
    else:
        try:
            intervention.planned_budget.calc_totals()
        except InterventionBudget.DoesNotExist:
            pass


@receiver(m2m_changed, sender=InterventionReview.prc_officers.through)
def create_review_for_prc_officer(sender, instance, action, reverse, pk_set, *args, **kwargs):
    if action == 'post_add':
        for pk in pk_set:
            PRCOfficerInterventionReview.objects.get_or_create(user_id=pk, overall_review=instance)
    elif action == 'post_remove':
        PRCOfficerInterventionReview.objects.filter(user_id__in=pk_set, overall_review=instance).delete()
