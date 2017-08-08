from django.core.management.base import BaseCommand

from vision.tasks import sync


class Command(BaseCommand):
    help = 'Syncs structures from VISION'

    def handle(self, *args, **options):
        sync()
