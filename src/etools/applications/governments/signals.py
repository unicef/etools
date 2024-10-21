from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from etools.applications.governments.models import (
    GDD,
    GDDBudget,
    GDDPRCOfficerReview,
    GDDReview,
    GDDSupplyItem,
    GDDTimeFrame,
)
from etools.applications.partners.utils import get_quarters_range

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


#
@receiver(post_save, sender=GDD)
def recalculate_time_frames(instance: GDD, created: bool, **kwargs):
    if instance.tracker.has_changed('start') or instance.tracker.has_changed('end'):
        old_quarters = get_quarters_range(instance.tracker.previous('start'), instance.tracker.previous('end'))
        new_quarters = get_quarters_range(instance.start, instance.end)

        # remove out of boundary frames
        if old_quarters and len(old_quarters) > len(new_quarters):
            if new_quarters:
                last_quarter = new_quarters[-1].quarter
            else:
                last_quarter = 0

            GDDTimeFrame.objects.filter(gdd=instance, quarter__gt=last_quarter).delete()

        # move existing ones
        for old_quarter, new_quarter in zip(old_quarters, new_quarters):
            GDDTimeFrame.objects.filter(
                gdd=instance, quarter=old_quarter.quarter
            ).update(
                start_date=new_quarter.start, end_date=new_quarter.end
            )

        # create missing if any
        for new_quarter in new_quarters[len(old_quarters):]:
            GDDTimeFrame.objects.get_or_create(
                gdd=instance, quarter=new_quarter.quarter,
                defaults={'start_date': new_quarter.start, 'end_date': new_quarter.end},
            )

#
# @receiver(post_delete, sender=InterventionActivity)
# def calc_totals_on_delete(instance, **kwargs):
#     try:
#         result = LowerResult.objects.get(pk=instance.result.pk)
#     except LowerResult.DoesNotExist:
#         pass
#     else:
#         try:
#             # update budgets
#             result.result_link.intervention.planned_budget.save()
#         except InterventionBudget.DoesNotExist:
#             pass
#
#
# @receiver(post_delete, sender=InterventionActivityItem)
# def update_cash_on_delete(instance, **kwargs):
#     try:
#         Activity = InterventionActivity.objects.get(pk=instance.activity.pk)
#     except InterventionActivity.DoesNotExist:
#         pass
#     else:
#         Activity.update_cash()
#
#
# @receiver(post_delete, sender=InterventionResultLink)
# def recalculate_result_links_numbering(instance, **kwargs):
#     InterventionResultLink.renumber_result_links_for_intervention(instance.intervention)
#     for result_link in instance.intervention.result_links.filter(id__gt=instance.id).prefetch_related(
#         'll_results',
#         'll_results__activities',
#         'll_results__activities__items',
#     ):
#         LowerResult.renumber_results_for_result_link(result_link)
#         for result in result_link.ll_results.all():
#             InterventionActivity.renumber_activities_for_result(result)
#             for activity in result.activities.all():
#                 InterventionActivityItem.renumber_items_for_activity(activity)
#
#
# @receiver(post_delete, sender=LowerResult)
# def recalculate_results_numbering(instance, **kwargs):
#     LowerResult.renumber_results_for_result_link(instance.result_link)
#     for result in instance.result_link.ll_results.filter(id__gt=instance.id).prefetch_related(
#         'activities',
#         'activities__items',
#     ):
#         InterventionActivity.renumber_activities_for_result(result)
#         for activity in result.activities.all():
#             InterventionActivityItem.renumber_items_for_activity(activity)


# @receiver(post_delete, sender=InterventionActivity)
# def recalculate_activities_numbering(instance, **kwargs):
#     InterventionActivity.renumber_activities_for_result(instance.result)
#     for activity in instance.result.activities.filter(id__gt=instance.id).prefetch_related('items'):
#         InterventionActivityItem.renumber_items_for_activity(activity)
#
#
# @receiver(post_delete, sender=InterventionActivityItem)
# def recalculate_items_numbering(instance, **kwargs):
#     InterventionActivityItem.renumber_items_for_activity(instance.activity)
