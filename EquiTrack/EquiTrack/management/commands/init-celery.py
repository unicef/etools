from django.core.management import BaseCommand

from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask


class Command(BaseCommand):
    help = 'Init celery command'

    def handle(self, *args, **options):
        every_day, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.DAYS)
        every_two_weeks, _ = IntervalSchedule.objects.get_or_create(every=14, period=IntervalSchedule.DAYS)
        every_week, _ = IntervalSchedule.objects.get_or_create(every=7, period=IntervalSchedule.DAYS)
        midnight, _ = CrontabSchedule.objects.get_or_create(minute=0, hour=0)

        PeriodicTask.objects.get_or_create(name='Hact Chart', defaults={
            'task': 'hact.tasks.update aggregate hact values',
            'interval': every_day})

        PeriodicTask.objects.get_or_create(name='Intervention Notification Ending', defaults={
            'task': 'partners.tasks.intervention_notification_ending',
            'interval': every_day})

        PeriodicTask.objects.get_or_create(name='Intervention Notification Ended frs Outstanding', defaults={
            'task': 'partners.tasks.intervention_notification_ended_fr_outstanding',
            'interval': every_two_weeks})

        PeriodicTask.objects.get_or_create(name='Intervention Notification Signed no frs', defaults={
            'task': 'partners.tasks.intervention_notification_signed_no_frs',
            'interval': every_week})

        PeriodicTask.objects.get_or_create(name='Intervention Status Automatic Transition', defaults={
            'task': 'partners.tasks.intervention_status_automatic_transition',
            'interval': every_day})

        PeriodicTask.objects.get_or_create(name='Agreement Status Automatic Transition', defaults={
            'task': 'partners.tasks.agreement_status_automatic_transition',
            'interval': every_day})

        PeriodicTask.objects.get_or_create(name='Vision Sync Task', defaults={
            'task': 'vision.tasks.vision_sync_task',
            'crontab': midnight})
