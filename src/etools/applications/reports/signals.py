from django.db.models.signals import post_save
from django.dispatch import receiver

from etools.applications.partners.models import Intervention
from etools.applications.partners.utils import get_quarters_range
from etools.applications.reports.models import InterventionTimeFrame


@receiver(post_save, sender=Intervention)
def recalculate_time_frames(instance: Intervention, created: bool, **kwargs):
    if instance.tracker.has_changed('start') or instance.tracker.has_changed('end'):
        old_quarters = get_quarters_range(instance.tracker.previous('start'), instance.tracker.previous('end'))
        new_quarters = get_quarters_range(instance.start, instance.end)

        # remove out of boundary frames
        if len(old_quarters) > len(new_quarters):
            InterventionTimeFrame.objects.filter(intervention=instance, quarter__gt=new_quarters[-1].quarter).delete()

        # move existing ones
        for old_quarter, new_quarter in zip(old_quarters, new_quarters):
            InterventionTimeFrame.objects.filter(
                intervention=instance, quarter=old_quarter.quarter
            ).update(
                start_date=new_quarter.start, end_date=new_quarter.start
            )

        # create missing if any
        for new_quarter in new_quarters[len(old_quarters):]:
            InterventionTimeFrame.objects.get_or_create(
                intervention=instance, quarter=new_quarter.quarter,
                defaults={'start_date': new_quarter.start, 'end_date': new_quarter.end},
            )
