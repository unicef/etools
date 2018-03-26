import logging

from django.core.management import BaseCommand
from django.db import connection, transaction

from users.models import Country

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clear Migration Table'

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
            logger.info(u'Clear table for %s' % country.name)
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM django_migrations WHERE app IN ('partners', 'trips', 'tpm', 't2f', 'audit',"
                               "'hact', 'workplan', 'activities', 'attachments', 'environment', 'firms', 'funds',"
                               "'locations', 'management', 'notification', 'publics', 'purchase_order', 'reports',"
                               "'snapshot', 'tpmpartners', 'supplies', 'users', 'vision')")

        logger.info(u'Command finished')
