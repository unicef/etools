
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from etools.applications.publics.management.commands.xml.travel_agents import TRAVEL_AGENTS_XML
from etools.applications.publics.tasks import import_travel_agents


class Command(BaseCommand):

    @atomic
    def handle(self, *args, **options):
        import_travel_agents(TRAVEL_AGENTS_XML)
