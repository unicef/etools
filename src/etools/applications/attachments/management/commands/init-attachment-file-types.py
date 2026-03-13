import logging

from django.core.management.base import BaseCommand
from django.db import connection

from unicef_attachments.models import FileType

from etools.applications.field_monitoring.fm_settings.models import FMDocumentTypeDescription
from etools.applications.users.models import Country
from etools.libraries.tenant_support.utils import run_on_all_tenants

logger = logging.getLogger(__name__)

FILE_TYPES_MAPPING = [
    # ("code", "label", "name", "order"),
    ("partners_agreement", "Signed Agreement", "attached_agreement", 0),
    ("partners_partner_assessment", "Core Values Assessment", "core_values_assessment", 0),
    ("partners_assessment_report", "Assessment Report", "assessment_report", 0),
    ("partners_agreement_amendment", "Agreement Amendment", "agreement_signed_amendment", 0),
    ("partners_intervention_prc_review", "PRC Review", "intervention_prc_review", 0),
    ("partners_intervention_signed_pd", "Signed PD/SPD", "intervention_signed_pd", 0),
    ("partners_intervention_activation_letter", "PD Activation Letter", "activation_letter", 0),
    ("partners_intervention_termination_doc", "PD Termination Document", "termination_doc", 0),
    ("partners_intervention_amendment_signed", "PD/SPD Amendment", "intervention_amendment_signed", 0),
    ("partners_intervention_attachment", "Intervention Attachment", "intervention_attachment", 0),
    ("t2f_travel_attachment", "Travel Attachment", "t2f_travel_attachment", 0),
]

# Legacy fm_common entries: update by pk to preserve backward compatibility with existing attachments.
# pk 2104 (was "Progress evidence") and pk 2105 (was "Bottleneck and Challenges") both merge into
# "Evidence & Verification". pk 2105 uses a unique name so it is excluded from the file-types
# dropdown while still displaying the correct label on existing attachments.
# pk 2106 (was "Reference documents") maps to "Pre-Visit Planning Documents".
FM_COMMON_LEGACY_TYPES = [
    # (pk, name, label, order)
    (2104, "evidence_verification", "Evidence & Verification of Results and Bottlenecks Documents", 5),
    (2105, "evidence_verification_legacy", "Evidence & Verification of Results and Bottlenecks Documents", 5),
    (2106, "pre_visit_planning", "Pre-Visit Planning Documents", 2),
]

# New fm_common entries: created/updated by (code, name).
FM_COMMON_NEW_TYPES = [
    # (name, label, order)
    ("administrative_compliance", "Administrative & Compliance Documents", 3),
    ("field_data_collection", "Field Data Collection Documents (beyond FM checklist)", 4),
    ("risk_safeguarding_protection", "Risk, Safeguarding & Protection Documents", 6),
    ("post_visit_documentation", "Post-Visit Documentation and Follow-up Action Plan", 7),
]

# Tooltip descriptions stored in FMDocumentTypeDescription, keyed by FileType.name.
FM_DOCUMENT_TYPE_DESCRIPTIONS = {
    "pre_visit_planning": (
        "These help frame the objectives and references to read before and carry during the visit.\n\n"
        "Examples include:\n"
        "\u2022 Visit Terms of Reference (ToR)\n"
        "\u2022 Monitoring checklist or tool (aligned with program indicators)\n"
        "\u2022 Workplan / Itinerary\n"
        "\u2022 Maps / Site lists / Location details\n"
        "\u2022 Previous monitoring reports for the same location or workplan activity/output\n"
        "\u2022 Previous Partner reports for triangulation"
    ),
    "administrative_compliance": (
        "To verify adherence to donor, organizational, and regulatory requirements.\n\n"
        "Examples include:\n"
        "\u2022 Partner agreements / MoUs / Previous Programme Document/Simplified Programme Document (PD/SPD) for the same partner\n"
        "\u2022 Procurement documents (POs, invoices, delivery notes)\n"
        "\u2022 Asset or inventory registers\n"
        "\u2022 Compliance checklists (if applicable)"
    ),
    "field_data_collection": (
        "Tools used on-site to record findings in addition to the FM checklist.\n\n"
        "Examples include:\n"
        "\u2022 Interview or FGD guides used\n"
        "\u2022 Enumerator/monitoring forms (digital or paper) including additional checklists used\n"
        "\u2022 Attendance sheets (for activities or training sessions)\n"
        "\u2022 Quality assurance (QA/QC) checklists beyond FMM checklist"
    ),
    "evidence_verification": (
        "Proof that activities took place as reported. To assess progress and alignment with program goals.\n\n"
        "Examples include:\n"
        "\u2022 Photographs with metadata (e.g., date, GPS)\n"
        "\u2022 GPS coordinates / maps\n"
        "\u2022 Signed beneficiary confirmations (when appropriate)\n"
        "\u2022 Delivery records / Distribution lists\n"
        "\u2022 Receipts, vouchers, or tokens\n"
        "\u2022 Infrastructure assessment sheets\n"
        "\u2022 Before/after photos (for construction or rehabilitation work)\n"
        "\u2022 Activity reports from partners\n"
        "\u2022 Training materials used in the field\n"
        "\u2022 Curricula or technical guidelines\n"
        "\u2022 Monitoring & Evaluation (M&E) indicator tables\n"
        "\u2022 Gender, protection, or safeguarding documentation"
    ),
    "risk_safeguarding_protection": (
        "Especially important for donor\u2011funded or protection\u2011sensitive programs.\n\n"
        "Examples include:\n"
        "\u2022 Incident reporting forms (not capturing beneficiary identity but trigger document)\n"
        "\u2022 Safeguarding compliance checklists\n"
        "\u2022 Protection mainstreaming tool\n"
        "\u2022 Risk assessment forms\n"
        "\u2022 PSEA (Protection from Sexual Exploitation and Abuse) guidance"
    ),
    "post_visit_documentation": (
        "To close the loop and document follow\u2011up.\n\n"
        "Examples include:\n"
        "\u2022 Field monitoring report (if anything beyond what the FMM report captures)\n"
        "\u2022 Action point tracker (with responsibility + deadline)\n"
        "\u2022 Partner feedback form\n"
        "\u2022 Follow\u2011up verification plan\n"
        "\u2022 Corrective action documentation"
    ),
}


class Command(BaseCommand):
    help = 'Init Attachment File Type command'

    def add_arguments(self, parser):
        parser.add_argument('--schema', dest='schema')

    def run(self):
        logger.info('Initialization for %s' % connection.schema_name)
        for code, label, name, order in FILE_TYPES_MAPPING:
            FileType.objects.update_or_create(
                code=code,
                defaults={
                    "label": label,
                    "name": name,
                    "order": order,
                }
            )
        for pk, name, label, order in FM_COMMON_LEGACY_TYPES:
            # Remove any stale rows with the same (name, code) that have a different pk.
            # These can be left over from earlier command runs that created entries by name.
            FileType.objects.filter(code='fm_common', name=name).exclude(pk=pk).delete()
            FileType.objects.update_or_create(
                pk=pk,
                defaults={
                    "code": "fm_common",
                    "name": name,
                    "label": label,
                    "order": order,
                }
            )
        for name, label, order in FM_COMMON_NEW_TYPES:
            FileType.objects.update_or_create(
                code='fm_common',
                name=name,
                defaults={
                    "label": label,
                    "order": order,
                }
            )
        for name, description in FM_DOCUMENT_TYPE_DESCRIPTIONS.items():
            FMDocumentTypeDescription.objects.update_or_create(
                name=name,
                defaults={"description": description},
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
