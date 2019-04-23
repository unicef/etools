from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from django_tenants.utils import get_tenant_domain_model

from etools.applications.publics.models import Currency
from etools.applications.users.models import Country


class Command(BaseCommand):
    help = 'Create a new country and related schema'

    def add_arguments(self, parser):
        parser.add_argument('country_name', type=str)

    def handle(self, *args, **options):
        try:
            name = options['country_name']
            slug = name.lower().replace(' ', '-').strip()
            usd = Currency.objects.get(code='USD')
            country = Country.objects.create(
                schema_name=name.lower().replace(' ', '_').strip(),
                name=name,
                local_currency=usd,
            )
            get_tenant_domain_model().objects.create(domain='{}.etools.unicef.org'.format(slug), tenant=country)
            call_command('init-result-type', schema=slug)
            call_command('init-partner-file-type', schema=slug)
            connection.set_schema(slug)
            call_command('loaddata', 'attachments_file_types')
            call_command('loaddata', 'audit_risks_blueprints')
            for user in get_user_model().objects.filter(is_superuser=True):
                user.profile.countries_available.add(country)
        except Exception as exp:
            raise CommandError(*exp.args)
