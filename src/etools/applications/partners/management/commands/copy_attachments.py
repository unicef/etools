
from django.core.management.base import BaseCommand

from etools.applications.partners.utils import copy_all_attachments


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            action="store",
            dest="days",
            help="Process attachments days ago",
            type=int,
        )
        parser.add_argument(
            "--hours",
            action="store",
            dest="hours",
            help="Process attachments hours ago",
            type=int,
        )
        parser.add_argument(
            "--all",
            action="store_true",
            dest="all",
            help="Process all attachments"
        )

    def handle(self, *args, **options):
        copy_all_attachments(**options)
