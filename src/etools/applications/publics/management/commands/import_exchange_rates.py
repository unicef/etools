
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from etools.applications.publics.management.commands.xml.exchange_rates import CURRENCY_XCHANGE_RATE_XML
from etools.applications.publics.tasks import import_exchange_rates


class Command(BaseCommand):

    @atomic
    def handle(self, *args, **options):
        import_exchange_rates(CURRENCY_XCHANGE_RATE_XML)
