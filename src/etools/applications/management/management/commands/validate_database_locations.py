from django.core.management.base import BaseCommand

from etools.libraries.locations.utils import validate_database_locations


class Command(BaseCommand):
    def handle(self, *args, **options):
        validate_database_locations()
