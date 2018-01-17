from django.core.management.base import BaseCommand, CommandError
from django.utils import six

from users.models import Country
from publics.models import Currency


class Command(BaseCommand):
    help = 'Create a new country and related schema'

    def add_arguments(self, parser):
        parser.add_argument('country_name', type=six.text_type)

    def handle(self, *args, **options):
        try:
            name = options['country_name']
            slug = name.lower().replace(' ', '-').strip()
            usd = Currency.objects.get(code='USD')
            Country.objects.create(
                domain_url='{}.etools.unicef.org'.format(slug),
                schema_name=name.lower().replace(' ', '_').strip(),
                name=name,
                local_currency=usd,
            )
        except Exception as exp:
            raise CommandError(exp.args[0])
