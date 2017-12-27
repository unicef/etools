from __future__ import absolute_import, division, print_function, unicode_literals

import json
from datetime import datetime

from django.core.management import BaseCommand
from django.db import transaction

from EquiTrack.util_scripts import set_country
from hact.models import HactEncoder, HactHistory
from partners.models import hact_default, PartnerOrganization
from users.models import Country


class Command(BaseCommand):
    help = 'Freeze Hact Data for Current Year'

    def add_arguments(self, parser):
        parser.add_argument('--schema', dest='schema')

    def freeze_data(self, hact_history):
        partner = hact_history.partner
        # partner values list needs to be in the
        # desired order for export results
        partner_values = [
            ('Implementing Partner', partner.name),
            ('Partner Type', partner.partner_type),
            ('Shared', partner.shared_partner),
            ('Shared IP', partner.shared_with),
            ('TOTAL for current CP cycle', partner.total_ct_cp),
            ('PLANNED for current year', partner.hact_values.get("planned_cash_transfer")),
            ('Current Year (1 Oct - 30 Sep)', partner.total_ct_cy),
            ('Micro Assessment', partner.hact_values.get("micro_assessment_needed")),
            ('Risk Rating', partner.rating),
            ('Programmatic Visits Planned', partner.hact_values.get("planned_visits")),
            ('Programmatic Visits M.R', partner.hact_min_requirements["programme_visits"]),
            ('Programmatic Visits Done', partner.hact_values.get("programmatic_visits")),
            ('Spot Checks M.R', partner.hact_min_requirements["spot_checks"]),
            ('Spot Checks Done', partner.hact_values.get("spot_checks")),
            ('Audits M.R', partner.hact_values.get("audits_mr")),
            ('Audits Done', partner.hact_values.get("audits_done")),
            ('Flag for Follow up', partner.hact_values.get("follow_up_flags")),
        ]
        hact_history.partner_values = json.dumps(partner_values, cls=HactEncoder)
        hact_history.save()

    @transaction.atomic
    def handle(self, *args, **options):

        countries = Country.objects.exclude(name__iexact='global')
        if options['schema']:
            countries = countries.filter(schema_name=options['schema'])

        year = datetime.now().year
        self.stdout.write('Freeze HACT data for {}'.format(year))

        for country in countries:
            set_country(country.name)
            self.stdout.write('Freezing data for {}'.format(country.name))
            for partner in PartnerOrganization.objects.all():
                hact_history, created = HactHistory.objects.get_or_create(partner=partner, year=year)
                if created:
                    self.freeze_data(hact_history)
                    partner.hact_values = hact_default()
                    partner.save()
