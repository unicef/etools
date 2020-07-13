import logging

from django.core.management.base import BaseCommand
from django.db import connection

from unicef_attachments.models import FileType

from etools.applications.users.models import Country
from etools.libraries.tenant_support.utils import run_on_all_tenants

logger = logging.getLogger(__name__)

FILE_TYPES_MAPPING = [
    # ("code", "label", "name", "order", "group"),
    ("partners_agreement", "Signed Agreement", "attached_agreement", 0, ["pmp"]),
    ("partners_partner_assessment", "Core Values Assessment", "core_values_assessment", 0, ["pmp"]),
    ("partners_assessment_report", "Assessment Report", "assessment_report", 0, ["pmp"]),
    ("partners_agreement_amendment", "Agreement Amendment", "agreement_signed_amendment", 0, ["pmp"]),
    ("partners_intervention_prc_review", "PRC Review", "intervention_prc_review", 0, ["pmp"]),
    ("partners_intervention_signed_pd", "Signed PD/SSFA", "intervention_signed_pd", 0, ["pmp"]),
    ("partners_intervention_activation_letter", "PD Activation Letter", "activation_letter", 0, ["pmp"]),
    ("partners_intervention_termination_doc", "PD Termination Document", "termination_doc", 0, ["pmp"]),
    ("partners_intervention_amendment_signed", "PD/SSFA Amendment", "intervention_amendment_signed", 0, ["pmp"]),
    ("partners_intervention_attachment", "Intervention Attachment", "intervention_attachment", 0, ["pmp"]),
    ("partners_agreement_termination_doc", "Termination document for PCAs", "termination_doc", 0, ["pmp"]),
    ("partners_intervention_amendment_internal_prc_review", "Internal PRC Review", "internal_prc_review", 0, ["pmp"]),
    ("t2f_travel_attachment", "Travel Attachment", "t2f_travel_attachment", 0, ["t2f"]),
]


class Command(BaseCommand):
    help = 'Init Attachment File Type command'

    def add_arguments(self, parser):
        parser.add_argument('--schema', dest='schema')

    def run(self):
        logger.info('Initialization for %s' % connection.schema_name)
        for code, label, name, order, group in FILE_TYPES_MAPPING:
            FileType.objects.update_or_create(
                code=code,
                defaults={
                    "label": label,
                    "name": name,
                    "order": order,
                    "group": group,
                }
            )

    def handle(self, *args, **options):

        logger.info('Command started')

        countries = Country.objects.exclude(name__iexact='global')
        if options['schema']:
            country = countries.get(schema_name=options['schema'])
            connection.set_tenant(country)
            self.run()
        else:
            run_on_all_tenants(self.run)

        logger.info('Command finished')
