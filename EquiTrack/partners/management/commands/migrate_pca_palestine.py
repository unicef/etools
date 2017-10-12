from django.core.management.base import BaseCommand

from django.db import connection

from partners.models import (
    Agreement,
    CountryProgramme
)

from users.models import Country


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            connection.set_tenant(Country.objects.get(schema_name="palestine"))
            cps = CountryProgramme.objects.filter(invalid=False, wbs__contains='/PC/')

            for cp in cps:
                Agreement.objects.filter(
                    start__gte=cp.from_date,
                    start__lte=cp.to_date,
                    country_programme__isnull=True
                ).exclude(agreement_type__in=['MOU']).update(country_programme=cp)
        except Country.DoesNotExist:
            print "The schema could not be set"
