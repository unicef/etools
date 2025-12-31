from datetime import datetime

from django.core.management import BaseCommand
from django.db import transaction

from etools.applications.core.util_scripts import set_country
from etools.applications.hact.models import HactHistory
from etools.applications.partners.models import hact_default, PartnerOrganization, PlannedEngagement
from etools.applications.users.models import Country


class Command(BaseCommand):
    help = 'Freeze Hact Data for Current Year'

    def add_arguments(self, parser):
        parser.add_argument('--schema', dest='schema')
        parser.add_argument('--year', dest='year', help='History year', type=int, default=datetime.now().year)

    def get_or_empty(self, hact_json, keys):
        value = hact_json
        try:
            for key in keys:
                value = value[key]
        except KeyError:
            print('----------------')
            return None
        return value

    def freeze_data(self, hact_history):
        # partner values list needs to be in the desired order for export results
        partner = hact_history.partner
        partner_hact = hact_history.partner.hact_values
        planned_engagement = getattr(partner, 'planned_engagement', {})
        partner_values = [
            ('Implementing Partner', partner.name),
            ('Vendor Number', partner.vendor_number),
            ('Partner Type', partner.partner_type),
            ('Shared IP', partner.shared_with),
            ('Assessment Type', partner.type_of_assessment),
            ('Cash Transfer 1 OCT - 30 SEP', partner.net_ct_cy),
            ('Liquidations 1 OCT - 30 SEP', partner.reported_cy),
            ('Cash Transfers Jan - Dec', partner.total_ct_ytd),
            ('Risk Rating', partner.rating),
            ('Expiring Threshold', partner.flags['expiring_assessment_flag']),
            ('Approach Threshold', partner.flags['approaching_threshold_flag']),
            ('Last PSEA Assess. Date', partner.psea_assessment_date),
            ('PSEA Risk Rating', partner.sea_risk_rating_name),
            ('Highest Risk Rating Type', partner.highest_risk_rating_type),
            ('Highest Risk Rating Name', partner.highest_risk_rating_name),
            ('Programmatic Visits Planned Q1',
             self.get_or_empty(partner_hact, ['programmatic_visits', 'planned', 'q1'])),
            ('Programmatic Visits Planned Q2',
             self.get_or_empty(partner_hact, ['programmatic_visits', 'planned', 'q2'])),
            ('Programmatic Visits Planned Q3',
             self.get_or_empty(partner_hact, ['programmatic_visits', 'planned', 'q3'])),
            ('Programmatic Visits Planned Q4',
             self.get_or_empty(partner_hact, ['programmatic_visits', 'planned', 'q4'])),
            ('Programmatic Visits M.R', partner.hact_min_requirements.get('programmatic_visits')),
            ('Programmatic Visits Completed Q1',
             self.get_or_empty(partner_hact, ['programmatic_visits', 'completed', 'q1'])),
            ('Programmatic Visits Completed Q2',
             self.get_or_empty(partner_hact, ['programmatic_visits', 'completed', 'q2'])),
            ('Programmatic Visits Completed Q3',
             self.get_or_empty(partner_hact, ['programmatic_visits', 'completed', 'q3'])),
            ('Programmatic Visits Completed Q4',
             self.get_or_empty(partner_hact, ['programmatic_visits', 'completed', 'q4'])),
            ('Spot Checks Planned Q1', getattr(planned_engagement, 'spot_check_planned_q1', None)),
            ('Spot Checks Planned Q2', getattr(planned_engagement, 'spot_check_planned_q2', None)),
            ('Spot Checks Planned Q3', getattr(planned_engagement, 'spot_check_planned_q3', None)),
            ('Spot Checks Planned Q4', getattr(planned_engagement, 'spot_check_planned_q4', None)),
            ('Spot Checks M.R', partner.hact_min_requirements.get('spot_checks')),
            ('Follow Up', getattr(planned_engagement, 'spot_check_follow_up', None)),
            ('Spot Checks Completed Q1', self.get_or_empty(partner_hact, ['spot_checks', 'completed', 'q1'])),
            ('Spot Checks Completed Q2', self.get_or_empty(partner_hact, ['spot_checks', 'completed', 'q2'])),
            ('Spot Checks Completed Q3', self.get_or_empty(partner_hact, ['spot_checks', 'completed', 'q3'])),
            ('Spot Checks Completed Q4', self.get_or_empty(partner_hact, ['spot_checks', 'completed', 'q4'])),
            ('Audits M.R', partner.hact_min_requirements.get('audits')),
            ('Audit Completed', self.get_or_empty(partner_hact, ['audits', 'completed'])),
            ('Audit Outstanding Findings', self.get_or_empty(partner_hact, ['outstanding_findings', ])),
        ]
        hact_history.partner_values = partner_values
        hact_history.save()

    @transaction.atomic
    def handle(self, *args, **options):

        countries = Country.objects.filter(name__in=['Global', 'MENARO'])
        if options['schema']:
            countries = countries.filter(schema_name=options['schema'])

        year = options.get('year')
        self.stdout.write('Freeze HACT data for {}'.format(year))

        for country in countries:
            set_country(country.name)
            self.stdout.write('Freezing data for {}'.format(country.name))
            for partner in PartnerOrganization.objects.all():
                if (partner.reported_cy and partner.reported_cy > 0) or (
                        partner.total_ct_cy and partner.total_ct_cy > 0):
                    hact_history, _ = HactHistory.objects.get_or_create(partner=partner, year=year)
                    self.freeze_data(hact_history)
                partner.hact_values = hact_default()
                partner.save()

                plan, _ = PlannedEngagement.objects.get_or_create(partner=partner)
                plan.reset()
