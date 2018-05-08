import logging

from django.core.management import BaseCommand
from django.db import connection, transaction

from etools.applications.users.models import Country

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

        etools_apps = ','.join(["'audit'", "'activities'", "'attachments'", "'environment'", "'firms'", "'funds'",
                                "'locations'", "'hact'", "'management'", "'notification'", "'partners'", "'publics'",
                                "'purchase_order'", "'reports'", "'snapshot'", "'t2f'", "'tpm'", "'tpmpartners'",
                                "'users'", "'vision'",
                                "'trips'", "'supplies'", "'workplan'"  # TODO remove these apps
                                ])
        for country in countries:
            connection.set_tenant(country)
            logger.info(u'Clear table for %s' % country.name)
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM django_migrations WHERE app IN ({})".format(etools_apps))

        logger.info(u'Command finished')
