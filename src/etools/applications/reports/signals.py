from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from etools.applications.partners.models import Intervention, InterventionResultLink
from etools.applications.reports.base import signals as base_signals
from etools.applications.reports.models import InterventionActivity, InterventionActivityItem, LowerResult


@receiver(post_save, sender=Intervention)
def recalculate_time_frames(instance: Intervention, created: bool, **kwargs):
    base_signals.recalculate_time_frames(instance, created, **kwargs)


@receiver(post_delete, sender=InterventionActivity)
def calc_totals_on_delete(instance, **kwargs):
    base_signals.calc_totals_on_delete(instance, **kwargs)


@receiver(post_delete, sender=InterventionActivityItem)
def update_cash_on_delete(instance, **kwargs):
    base_signals.update_cash_on_delete(instance, **kwargs)


@receiver(post_delete, sender=InterventionResultLink)
def recalculate_result_links_numbering(instance, **kwargs):
    base_signals.recalculate_result_links_numbering(instance, **kwargs)


@receiver(post_delete, sender=LowerResult)
def recalculate_results_numbering(instance, **kwargs):
    base_signals.recalculate_results_numbering(instance, **kwargs)


@receiver(post_delete, sender=InterventionActivity)
def recalculate_activities_numbering(instance, **kwargs):
    base_signals.recalculate_activities_numbering(instance, **kwargs)


@receiver(post_delete, sender=InterventionActivityItem)
def recalculate_items_numbering(instance, **kwargs):
    base_signals.recalculate_items_numbering(instance, **kwargs)
