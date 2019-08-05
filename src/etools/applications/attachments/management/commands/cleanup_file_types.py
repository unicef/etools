from django.core.management.base import BaseCommand
from django.db import connection

from unicef_attachments.utils import cleanup_filetypes

from etools.applications.users.models import Country
from etools.libraries.tenant_support.utils import run_on_all_tenants


class Command(BaseCommand):
    help = 'Clean File Types command'

    def add_arguments(self, parser):
        parser.add_argument('--schema', dest='schema')

    def run(self):
        cleanup_filetypes()

    def handle(self, *args, **options):
        if options['schema']:
            countries = Country.objects.exclude(name__iexact='global')
            country = countries.get(schema_name=options['schema'])
            connection.set_tenant(country)
            self.run()
        else:
            run_on_all_tenants(self.run)
