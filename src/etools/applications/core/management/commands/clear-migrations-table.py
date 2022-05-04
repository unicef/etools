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

        logger.info('Command started')

        countries = Country.objects.all()
        if options['schema']:
            countries = countries.filter(schema_name=options['schema'])

        etools_apps = ','.join([
            "'action_points'",
            "'activities'",
            "'attachments'",
            "'audit'",
            "'categories'",
            "'comments'",
            "'core'",
            "'environment'",
            "'field_monitoring_da_collection'",
            "'field_monitoring_planning'",
            "'field_monitoring_settings'",
            "'firms'",
            "'funds'",
            "'locations'",
            "'hact'",
            "'management'",
            "'partners'",
            "'permissions2'",
            "'psea'",
            "'publics'",
            "'purchase_order'",
            "'reports'",
            "'t2f'",
            "'tpm'",
            "'tpmpartners'",
            "'travel'",
            "'users'",
            "'vision'",
        ])
        for country in countries:
            connection.set_tenant(country)
            logger.info('Clear table for %s' % country.name)
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM django_migrations WHERE app IN ({}) AND name!='0001_initial'".format(etools_apps))
                cursor.execute(
                    "INSERT INTO django_migrations(app, name, applied) VALUES ('activities', '0002_initial', 'now()');")

        logger.info('Command finished')
