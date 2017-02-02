from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from publics.tasks import import_cost_assignments
from .xml.cost_assignments import COST_ASSIGNMENTS_XML


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('xml_path', nargs=1)

    @atomic
    def handle(self, *args, **options):
        import_cost_assignments(COST_ASSIGNMENTS_XML)
