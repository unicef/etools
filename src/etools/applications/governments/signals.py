from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from etools.applications.governments.models import GDD, GDDBudget, GDDPRCOfficerReview, GDDReview, GDDSupplyItem

# TODO clean up: endpoint removed in prp
# @receiver(post_save, sender=GDD)
# def sync_pd_partner_to_prp(instance: GDD, created: bool, **kwargs):
#     if instance.date_sent_to_partner and instance.tracker.has_changed('date_sent_to_partner'):
#         sync_partner_to_prp.delay(connection.tenant.name, instance.agreement.partner_id)


@receiver(post_delete, sender=GDDSupplyItem)
def calc_totals_on_delete(instance, **kwargs):
    try:
        gdd = GDD.objects.get(pk=instance.gdd.pk)
    except GDD.DoesNotExist:
        pass
    else:
        try:
            # update budgets
            gdd.planned_budget.save()
        except GDDBudget.DoesNotExist:
            pass


@receiver(m2m_changed, sender=GDDReview.prc_officers.through)
def create_review_for_prc_officer(sender, instance, action, reverse, pk_set, *args, **kwargs):
    if action == 'post_add':
        for pk in pk_set:
            GDDPRCOfficerReview.objects.get_or_create(user_id=pk, overall_review=instance)
    elif action == 'post_remove':
        GDDPRCOfficerReview.objects.filter(user_id__in=pk_set, overall_review=instance).delete()


@receiver(m2m_changed, sender=GDD.unicef_focal_points.through)
def sync_unicef_focal_points_to_amendment(sender, instance: GDD, action, reverse, pk_set, *args, **kwargs):
    # TODO: migrate legacy records to have amendments is_active False
    active_amendments = instance.amendments.filter(is_active=True, amended_gdd__isnull=False)

    for amendment in active_amendments:
        if action == 'post_add':
            amendment.amended_gdd.unicef_focal_points.add(*pk_set)
        elif action == 'post_remove':
            amendment.amended_gdd.unicef_focal_points.remove(*pk_set)


@receiver(m2m_changed, sender=GDD.partner_focal_points.through)
def sync_partner_focal_points_to_amendment(sender, instance: GDD, action, reverse, pk_set, *args, **kwargs):
    active_amendments = instance.amendments.filter(is_active=True)

    for amendment in active_amendments:
        if action == 'post_add':
            amendment.amended_gdd.partner_focal_points.add(*pk_set)
        elif action == 'post_remove':
            amendment.amended_gdd.partner_focal_points.remove(*pk_set)


@receiver(post_save, sender=GDD)
def sync_budget_owner_to_amendment(instance: GDD, created: bool, **kwargs):
    if instance.budget_owner_id and instance.tracker.has_changed('budget_owner'):
        for amendment in instance.amendments.filter(is_active=True):
            amendment.amended_gdd.budget_owner_id = instance.budget_owner_id
            amendment.amended_gdd.save()
