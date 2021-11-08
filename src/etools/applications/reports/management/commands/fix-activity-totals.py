import logging

from django.core.management import BaseCommand
from django.db import connection, transaction
from django.db.models import Count

from etools.applications.reports.models import InterventionActivity
from etools.applications.users.models import Country

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Init ResultType command'

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
            logger.info('Running for %s' % country.name)
            for activity in InterventionActivity.objects.annotate(items_count=Count('items')).filter(items_count__gte=1):
                activity.update_cash()

        logger.info('Command finished')
