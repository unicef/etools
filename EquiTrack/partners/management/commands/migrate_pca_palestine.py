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

        except Country.DoesNotExist:
            print("The schema could not be set")

        else:
            cps = CountryProgramme.objects.filter(invalid=False, wbs__contains='/PC/')

            for cp in cps:
                Agreement.objects.filter(
                    start__gte=cp.from_date,
                    start__lte=cp.to_date,
                    country_programme__isnull=True
                ).exclude(agreement_type__in=['MOU']).update(country_programme=cp)

            Agreement.objects.filter(country_programme__isnull=False,
                                     agreement_type__in=['MOU']).update(country_programme=None)

            bad_agreements = Agreement.objects.filter(country_programme__isnull=True, agreement_type='PCA')
            print("Number of Bad Agreements: {}".format(bad_agreements.count()))
            print("Ids {}".format(', '.join([a.id for a in bad_agreements.all()])))
