import logging

from django.core.management import BaseCommand
from django.db import connection, transaction

from reports.models import ResultType
from users.models import Country

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Init ResultType command'

    def add_arguments(self, parser):
        parser.add_argument('--schema', dest='schema')

    @transaction.atomic
    def handle(self, *args, **options):

        logger.info(u'Command started')

        countries = Country.objects.exclude(name__iexact='global')
        if options['schema']:
            countries = countries.filter(schema_name=options['schema'])

        for country in countries:
            connection.set_tenant(country)
            logger.info(u'Initialization for %s' % country.name)
            ResultType.objects.get_or_create(name=ResultType.OUTPUT)
            ResultType.objects.get_or_create(name=ResultType.OUTCOME)
            ResultType.objects.get_or_create(name=ResultType.ACTIVITY)

        logger.info(u'Command finished')
