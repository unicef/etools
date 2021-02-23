import logging

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from django_tenants.utils import get_tenant_domain_model

from etools.applications.publics.models import Currency
from etools.applications.users.models import Country

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create a new country and related schema'

    def add_arguments(self, parser):
        parser.add_argument('country_name', type=str)
        parser.add_argument('business_area_code', type=str)

    def handle(self, *args, **options):
        logger.info('Command started')
        try:
            name = options['country_name']
            business_area_code = options['business_area_code']
            logger.info(f'Creating {name} {business_area_code}')
            slug = name.lower().replace(' ', '-').strip()
            usd = Currency.objects.get(code='USD')
            schema_name = name.lower().replace(' ', '_').strip()
            country = Country.objects.create(
                schema_name=schema_name,
                name=name,
                local_currency=usd,
                business_area_code=business_area_code
            )
            get_tenant_domain_model().objects.create(domain='{}.etools.unicef.org'.format(slug), tenant=country)
            logger.info('Initializing models')
            call_command('init-result-type', schema=schema_name)
            call_command('init-partner-file-type', schema=schema_name)
            call_command('init-attachment-file-types', schema=schema_name)
            connection.set_schema(schema_name)

            logger.info('Loading fixtures')
            call_command('loaddata', 'psea_indicators')
            call_command('loaddata', 'attachments_file_types')
            call_command('loaddata', 'audit_risks_blueprints')
            for user in get_user_model().objects.filter(is_superuser=True):
                user.profile.countries_available.add(country)

        except BaseException as exp:
            raise CommandError(*exp.args)

        logger.info('Command finished')
