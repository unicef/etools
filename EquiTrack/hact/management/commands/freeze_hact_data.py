from __future__ import absolute_import, division, print_function, unicode_literals

import json
from datetime import datetime

from django.core.management import BaseCommand
from django.utils.translation import ugettext as _

from hact.models import HactEncoder, HactHistory

from EquiTrack.util_scripts import set_country
from partners.models import hact_default, PartnerOrganization
from users.models import Country


class Command(BaseCommand):
    help = 'Freeze Hact Data for Current Year'

    def add_arguments(self, parser):
        parser.add_argument('--schema', dest='schema')

    mapping_labels = {
        'name': _('Implementing Partner'),
        'partner_type': _('Partner Type'),
        'shared_partner': _('Shared'),
        'shared_with': _('Shared IP'),
        'total_ct_cp': _('TOTAL for current CP cycle'),
        'hact_values.planned_cash_transfer': _('PLANNED for current year'),
        'total_ct_cy': _('Current Year (1 Oct - 30 Sep)'),
        'hact_values.micro_assessment_needed': _('Micro Assessment'),
        'rating': _('Risk Rating'),
        'hact_values.planned_visits': _('Programmatic Visits Planned'),
        'hact_min_requirements.programme_visits': _('Programmatic Visits M.R'),
        'hact_values.programmatic_visits.completed.total': _('Programmatic Visits Done'),
        'hact_min_requirements.spot_checks': _('Spot Checks M.R'),
        'hact_values.spot_checks.completed.total': _('Spot Checks Done'),
        'hact_values.audits.completed': _('Audits M.R'),
        'hact_values.audits.required': _('Audits Done'),
        'hact_values.follow_up_flags': _('Flag for Follow up'),
    }

    @staticmethod
    def update_legacy_json(hact_json):

        hact_json['programmatic_visits_v1'] = hact_json.pop('programmatic_visits')
        hact_json['spot_checks_v1'] = hact_json.pop('spot_checks')

        v2_hact = hact_default()
        for key, value in v2_hact.items():
            if key in hact_json:
                raise Exception('Key is already there')
            hact_json[key] = value

        hact_json['programmatic_visits']['completed']['total'] = hact_json['programmatic_visits_v1']
        hact_json['programmatic_visits']['planned']['total'] = hact_json['planned_visits']
        hact_json['spot_checks']['completed']['total'] = hact_json['spot_checks_v1']

        hact_json['audits']['required'] = hact_json['audits_mr']
        hact_json['audits']['completed'] = hact_json['audits_done']

        return hact_json

    def freeze_data(self, hact_history):
        partner_values = {}

        for field_name, label in self.mapping_labels.items():
            fields = field_name.split('.')

            value = hact_history.partner

            partner_attribute = fields.pop(0)
            value = getattr(value, partner_attribute)
            for field in fields:
                value = value.get(field)

            partner_values[label] = value

        mrpv = value['hact_min_requirements']['programme_visits']
        mrsp = value['hact_min_requirements']['spot_checks']

        partner_values['hact_values']['programmatic_visits']['minumum_requirements'] = mrpv
        partner_values['hact_values']['spot_checks']['minumum_requirements'] = mrsp

        hact_history.partner_values = json.dumps(partner_values, cls=HactEncoder)
        hact_history.save()

    def handle(self, *args, **options):

        countries = Country.objects.exclude(schema_name='global')
        if options['schema']:
            countries = countries.filter(schema_name=options['schema'])

        year = datetime.now().year
        self.stdout.write('Freeze HACT data for {}'.format(year))

        for country in countries:
            set_country(country.name)
            self.stdout.write('Freezeing data for {}'.format(country.name))
            for partner in PartnerOrganization.objects.all():
                hact_history, created = HactHistory.objects.get_or_create(partner=partner, year=year)
                if created:
                    partner.hact_values = self.update_legacy_json(partner.hact_values)
                    partner.save()

                    self.freeze_data(hact_history)

                    partner.hact_values = hact_default()
                    partner.save()
