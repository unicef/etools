from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection, DEFAULT_DB_ALIAS

from tenant_schemas.utils import get_tenant_model


class Command(BaseCommand):
    help = "Wrapper around django loaddata for use with all tenants"

    def add_arguments(self, parser):
        parser.add_argument('args', metavar='fixture', nargs='+',
                            help='Fixture labels.')
        parser.add_argument('--database', action='store', dest='database',
                            default=DEFAULT_DB_ALIAS, help='Nominates a specific database to load '
                            'fixtures into. Defaults to the "default" database.')
        parser.add_argument('--app', action='store', dest='app_label',
                            default=None, help='Only look for fixtures in the specified app.')
        parser.add_argument('--ignorenonexistent', '-i', action='store_true',
                            dest='ignore', default=False,
                            help='Ignores entries in the serialized data for fields that do not '
                            'currently exist on the model.')

    def handle(self, *args, **options):
        all_tenants = get_tenant_model().objects.exclude(schema_name='public')

        for tenant in all_tenants:
            connection.set_tenant(tenant)
            call_command('loaddata', *args, **options)
