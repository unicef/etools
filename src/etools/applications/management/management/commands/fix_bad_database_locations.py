from django.core.management.base import BaseCommand

from etools.libraries.locations.utils import fix_bad_database_locations


class Command(BaseCommand):
    def handle(self, *args, **options):
        fix_bad_database_locations()
