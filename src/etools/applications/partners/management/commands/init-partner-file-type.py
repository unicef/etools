import logging

from django.core.management import BaseCommand
from django.db import connection

from etools.applications.partners.models import FileType
from etools.applications.users.models import Country
from etools.libraries.tenant_support.utils import run_on_all_tenants

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Init Partner File Type command'

    def add_arguments(self, parser):
        parser.add_argument('--schema', dest='schema')

    def run(self):
        logger.info('Initialization for %s' % connection.schema_name)
        for code, _display_name in FileType.NAME_CHOICES:
            FileType.objects.get_or_create(name=code)

    def handle(self, *args, **options):

        logger.info('Command started')

        countries = Country.objects.exclude(name__iexact='global')
        if options['schema']:
            country = countries.get(schema_name=options['schema'])
            connection.set_tenant(country)
            self.run()
        else:
            run_on_all_tenants(self.run)

        logger.info('Command finished')
