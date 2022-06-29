from django.apps import apps

from .quarters import get_quarters_range

InterventionBudget = apps.get_model('partners', 'InterventionBudget')
InterventionResultLink = apps.get_model('partners', 'InterventionResultLink')
LowerResult = apps.get_model('reports', 'LowerResult')
InterventionActivity = apps.get_model('reports', 'InterventionActivity')
InterventionActivityItem = apps.get_model('reports', 'InterventionActivityItem')
InterventionTimeFrame = apps.get_model('reports', 'InterventionTimeFrame')


def recalculate_time_frames(instance, created: bool, **kwargs):
    if instance.tracker.has_changed('start') or instance.tracker.has_changed('end'):
        old_quarters = get_quarters_range(instance.tracker.previous('start'), instance.tracker.previous('end'))
        new_quarters = get_quarters_range(instance.start, instance.end)

        # remove out of boundary frames
        if old_quarters and len(old_quarters) > len(new_quarters):
            if new_quarters:
                last_quarter = new_quarters[-1].quarter
            else:
                last_quarter = 0

            InterventionTimeFrame.objects.filter(intervention=instance, quarter__gt=last_quarter).delete()

        # move existing ones
        for old_quarter, new_quarter in zip(old_quarters, new_quarters):
            InterventionTimeFrame.objects.filter(
                intervention=instance, quarter=old_quarter.quarter
            ).update(
                start_date=new_quarter.start, end_date=new_quarter.end
            )

        # create missing if any
        for new_quarter in new_quarters[len(old_quarters):]:
            InterventionTimeFrame.objects.get_or_create(
                intervention=instance, quarter=new_quarter.quarter,
                defaults={'start_date': new_quarter.start, 'end_date': new_quarter.end},
            )


def calc_totals_on_delete(instance, **kwargs):
    try:
        result = LowerResult.objects.get(pk=instance.result.pk)
    except LowerResult.DoesNotExist:
        pass
    else:
        try:
            result.result_link.intervention.planned_budget.calc_totals()
        except InterventionBudget.DoesNotExist:
            pass


def update_cash_on_delete(instance, **kwargs):
    try:
        Activity = InterventionActivity.objects.get(pk=instance.activity.pk)
    except InterventionActivity.DoesNotExist:
        pass
    else:
        Activity.update_cash()


def recalculate_result_links_numbering(instance, **kwargs):
    InterventionResultLink.renumber_result_links_for_intervention(instance.intervention)
    for result_link in instance.intervention.result_links.filter(id__gt=instance.id).prefetch_related(
            'll_results',
            'll_results__activities',
            'll_results__activities__items',
    ):
        LowerResult.renumber_results_for_result_link(result_link)
        for result in result_link.ll_results.all():
            InterventionActivity.renumber_activities_for_result(result)
            for activity in result.activities.all():
                InterventionActivityItem.renumber_items_for_activity(activity)


def recalculate_results_numbering(instance, **kwargs):
    LowerResult.renumber_results_for_result_link(instance.result_link)
    for result in instance.result_link.ll_results.filter(id__gt=instance.id).prefetch_related(
            'activities',
            'activities__items',
    ):
        InterventionActivity.renumber_activities_for_result(result)
        for activity in result.activities.all():
            InterventionActivityItem.renumber_items_for_activity(activity)


def recalculate_activities_numbering(instance, **kwargs):
    InterventionActivity.renumber_activities_for_result(instance.result)
    for activity in instance.result.activities.filter(id__gt=instance.id).prefetch_related('items'):
        InterventionActivityItem.renumber_items_for_activity(activity)


def recalculate_items_numbering(instance, **kwargs):
    InterventionActivityItem.renumber_items_for_activity(instance.activity)
