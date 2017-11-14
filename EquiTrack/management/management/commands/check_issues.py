from django.core.management import BaseCommand

from management.issues.checks import run_all_checks


class Command(BaseCommand):
    help = 'Run all configured issue checks'

    def handle(self, *args, **options):
        run_all_checks()
