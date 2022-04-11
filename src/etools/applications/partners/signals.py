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


@receiver(m2m_changed, sender=Intervention.unicef_focal_points.through)
def sync_unicef_focal_points_to_amendment(sender, instance: Intervention, action, reverse, pk_set, *args, **kwargs):
    # TODO: migrate legacy records to have amendments is_active False
    active_amendments = instance.amendments.filter(is_active=True, amended_intervention__isnull=False)

    for amendment in active_amendments:
        if action == 'post_add':
            amendment.amended_intervention.unicef_focal_points.add(*pk_set)
        elif action == 'post_remove':
            amendment.amended_intervention.unicef_focal_points.remove(*pk_set)


@receiver(m2m_changed, sender=Intervention.partner_focal_points.through)
def sync_partner_focal_points_to_amendment(sender, instance: Intervention, action, reverse, pk_set, *args, **kwargs):
    active_amendments = instance.amendments.filter(is_active=True)

    for amendment in active_amendments:
        if action == 'post_add':
            amendment.amended_intervention.partner_focal_points.add(*pk_set)
        elif action == 'post_remove':
            amendment.amended_intervention.partner_focal_points.remove(*pk_set)


@receiver(post_save, sender=Intervention)
def sync_budget_owner_to_amendment(instance: Intervention, created: bool, **kwargs):
    if instance.budget_owner_id and instance.tracker.has_changed('budget_owner'):
        for amendment in instance.amendments.filter(is_active=True):
            amendment.amended_intervention.budget_owner_id = instance.budget_owner_id
            amendment.amended_intervention.save()
