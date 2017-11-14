from django.core.management.base import BaseCommand

from vision.tasks import vision_sync_task


class Command(BaseCommand):
    help = 'Syncs structures from VISION'

    def handle(self, *args, **options):
        vision_sync_task()
