from django.core.management import BaseCommand

from etools.applications.management.issues.checks import recheck_all_open_issues


class Command(BaseCommand):
    help = 'Recheck all open FlaggedIssues'

    def handle(self, *args, **options):
        recheck_all_open_issues()
