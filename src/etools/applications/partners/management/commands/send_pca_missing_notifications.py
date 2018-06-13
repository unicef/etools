from django.core.management.base import BaseCommand

from etools.applications.partners.utils import send_pca_missing_notifications


class Command(BaseCommand):
    def handle(self, *args, **options):
        send_pca_missing_notifications()
