
from django.core.management.base import BaseCommand

from partners.utils import copy_all_attachments


class Command(BaseCommand):
    def handle(self, *args, **options):
        copy_all_attachments()
