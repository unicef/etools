from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from publics.management.commands.xml.travel_agents import TRAVEL_AGENTS_XML
from publics.tasks import import_travel_agents


class Command(BaseCommand):

    @atomic
    def handle(self, *args, **options):
        import_travel_agents(TRAVEL_AGENTS_XML)
