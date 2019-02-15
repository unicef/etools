import logging

from django.core.management import BaseCommand
from django.db import connection, transaction

from etools.applications.partners.models import FileType
from etools.applications.users.models import Country

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Init Partner File Type command'

    def add_arguments(self, parser):
        parser.add_argument('--schema', dest='schema')

    @transaction.atomic
    def handle(self, *args, **options):

        logger.info('Command started')

        countries = Country.objects.exclude(name__iexact='global')
        if options['schema']:
            countries = countries.filter(schema_name=options['schema'])

        for country in countries:
            connection.set_tenant(country)
            logger.info('Initialization for %s' % country.name)

            for _, name in FileType.NAME_CHOICES:
                FileType.objects.get_or_create(name=name)

        logger.info('Command finished')
