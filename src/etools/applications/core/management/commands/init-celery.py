import logging

from django.core.management import BaseCommand

from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Init celery command'

    def handle(self, *args, **options):
        logger.info('Init Celery command started')
        every_day, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.DAYS)
        every_two_weeks, _ = IntervalSchedule.objects.get_or_create(every=14, period=IntervalSchedule.DAYS)
        every_week, _ = IntervalSchedule.objects.get_or_create(every=7, period=IntervalSchedule.DAYS)
        midnight, _ = CrontabSchedule.objects.get_or_create(minute=0, hour=0)
        first_day_of_the_month, _ = CrontabSchedule.objects.get_or_create(day_of_month=1, hour=1)

        PeriodicTask.objects.get_or_create(name='Hact Chart', defaults={
            'task': 'hact.tasks.update_aggregate_hact_values',
            'enabled': False,
            'interval': every_day})

        PeriodicTask.objects.get_or_create(name='Hact Values', defaults={
            'task': 'hact.tasks.update_hact_values',
            'enabled': False,
            'interval': every_day})

        PeriodicTask.objects.get_or_create(name='Notification Partner Assessment expires', defaults={
            'task': 'partners.tasks.notify_partner_assessment_expires',
            'enabled': False,
            'interval': every_day})

        PeriodicTask.objects.get_or_create(name='Intervention Notification Ending', defaults={
            'task': 'partners.tasks.intervention_notification_ending',
            'enabled': False,
            'interval': every_day})

        PeriodicTask.objects.get_or_create(name='Intervention Notification Ended frs Outstanding', defaults={
            'task': 'partners.tasks.intervention_notification_ended_fr_outstanding',
            'enabled': False,
            'interval': every_two_weeks})

        PeriodicTask.objects.get_or_create(name='Intervention Notification Signed no frs', defaults={
            'task': 'partners.tasks.intervention_notification_signed_no_frs',
            'enabled': False,
            'interval': every_week})

        PeriodicTask.objects.get_or_create(name='Intervention Status Automatic Transition', defaults={
            'task': 'partners.tasks.intervention_status_automatic_transition',
            'enabled': False,
            'interval': every_day})

        PeriodicTask.objects.get_or_create(name='Agreement Status Automatic Transition', defaults={
            'task': 'partners.tasks.agreement_status_automatic_transition',
            'enabled': False,
            'interval': every_day})

        PeriodicTask.objects.get_or_create(name='Vision Sync Task', defaults={
            'task': 'vision.tasks.vision_sync_task',
            'enabled': False,
            'crontab': midnight})

        PeriodicTask.objects.get_or_create(name='Update users with Azure', defaults={
            'task': 'azure_graph_api.tasks.sync_delta_users',
            'enabled': False,
            'crontab': midnight})

        PeriodicTask.objects.get_or_create(name='User Report', defaults={
            'task': 'users.tasks.user_report',
            'enabled': False,
            'crontab': first_day_of_the_month})

        PeriodicTask.objects.get_or_create(name='PMP Indicator Report', defaults={
            'task': 'partners.tasks.pmp_indicator_report',
            'enabled': False,
            'crontab': first_day_of_the_month})

        PeriodicTask.objects.get_or_create(name='Deactivate inactive users', defaults={
            'task': 'users.tasks.deactivate_stale_users',
            'enabled': False,
            'interval': every_two_weeks})

        logger.info('Init Celery command finished')
