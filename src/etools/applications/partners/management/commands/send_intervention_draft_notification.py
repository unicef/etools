from django.core.management.base import BaseCommand

from etools.applications.partners.utils import send_intervention_draft_notification


class Command(BaseCommand):
    def handle(self, *args, **options):
        send_intervention_draft_notification()
