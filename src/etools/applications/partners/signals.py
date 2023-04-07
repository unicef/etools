import datetime

from django.db import connection, transaction
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from etools.applications.partners.models import (
    Intervention,
    InterventionBudget,
    InterventionReview,
    InterventionSupplyItem,
    PRCOfficerInterventionReview,
)
from etools.applications.partners.tasks import sync_partner_to_prp, sync_realms_to_prp
from etools.applications.users.models import Realm


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
            # update budgets
            intervention.planned_budget.save()
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


@receiver(post_save, sender=Realm)
def sync_realms_to_prp_on_update(instance: Realm, created: bool, **kwargs):
    if instance.user.is_unicef_user():
        # only external users are allowed to be synced to prp
        return

    transaction.on_commit(
        lambda:
            sync_realms_to_prp.apply_async(
                (instance.user_id, instance.modified.timestamp()),
                eta=instance.modified + datetime.timedelta(minutes=5)
            )
    )


@receiver(post_delete, sender=Realm)
def sync_realms_to_prp_on_delete(instance: Realm, **kwargs):
    if instance.user.is_unicef_user():
        # only external users are allowed to be synced to prp
        return

    now = timezone.now()
    transaction.on_commit(
        lambda:
            sync_realms_to_prp.apply_async(
                (instance.user_id, now.timestamp()),
                eta=now + datetime.timedelta(minutes=5)
            )
    )
