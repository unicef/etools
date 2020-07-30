from django.db.models.signals import post_save
from django.dispatch import receiver

from etools.applications.partners.models import Intervention
from etools.applications.partners.utils import get_quarters_range
from etools.applications.reports.models import InterventionActivityTimeFrame


@receiver(post_save, sender=Intervention)
def recalculate_time_frames(instance: Intervention, created: bool, **kwargs):
    if not created and (instance.tracker.has_changed('start') or instance.tracker.has_changed('end')):
        old_quarters = get_quarters_range(instance.tracker.previous('start'), instance.tracker.previous('end'))
        new_quarters = get_quarters_range(instance.start, instance.end)

        # remove out of boundary frames
        if len(old_quarters) > len(new_quarters):
            InterventionActivityTimeFrame.objects.filter(
                activity__result__result_link__intervention=instance, start_date__gte=old_quarters[len(new_quarters)][0]
            ).delete()

        # move existing ones
        for old_quarter, new_quarter in zip(old_quarters, new_quarters):
            InterventionActivityTimeFrame.objects.filter(
                activity__result__result_link__intervention=instance,
                start_date=old_quarter[0], end_date=old_quarter[1]
            ).update(
                start_date=new_quarter[0], end_date=new_quarter[1]
            )
