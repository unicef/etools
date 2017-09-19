from django.core.management import BaseCommand
from datetime import date, datetime, timedelta
from users.models import Country, User
from management.models import FlaggedIssue
from management.issues.checks import get_issue_checks


class Command(BaseCommand):
    help = 'Run all configured issue checks'

    def handle(self, *args, **options):
        for issue_check in get_issue_checks():
            issue_check.check_all()
