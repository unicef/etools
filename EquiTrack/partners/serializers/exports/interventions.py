from __future__ import unicode_literals

from django.utils.translation import ugettext as _
from rest_framework import serializers

from locations.models import Location
from locations.serializers import (
    LocationExportFlatSerializer,
    LocationExportSerializer,
)
from partners.models import (
    Intervention,
    InterventionAmendment,
    InterventionResultLink,
)
from partners.serializers.fields import TypeArrayField
from partners.serializers.interventions_v2 import (
    InterventionAmendmentCUSerializer,
    InterventionResultSerializer,
)
from reports.models import Indicator
from reports.serializers.exports import (
    IndicatorExportFlatSerializer,
    IndicatorExportSerializer,
)


class InterventionAmendmentExportSerializer(InterventionAmendmentCUSerializer):
    types = TypeArrayField(label=_("Types"))

    class Meta:
        model = InterventionAmendment
        fields = "__all__"


class InterventionAmendmentExportFlatSerializer(InterventionAmendmentExportSerializer):
    intervention = serializers.CharField(
        label=_("Reference Number"),
        source="intervention.number",
    )


class InterventionSectorLocationLinkExportSerializer(LocationExportSerializer):
    intervention = serializers.SerializerMethodField(
        label=_("Reference Number")
    )
    sector = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = "__all__"

    def get_intervention(self, obj):
        return ",".join(
            [str(x.intervention.pk)
             for x in obj.intervention_sector_locations.all()]
        )

    def get_sector(self, obj):
        return ",".join(
            [str(x.sector.pk) for x in obj.intervention_sector_locations.all()]
        )


class InterventionSectorLocationLinkExportFlatSerializer(LocationExportFlatSerializer):
    intervention = serializers.SerializerMethodField(
        label=_("Reference Number"),
    )
    sector = serializers.SerializerMethodField(label=_("Sector"))

    class Meta:
        model = Location
        fields = "__all__"

    def get_intervention(self, obj):
        return ",".join(
            [str(x.intervention.number)
             for x in obj.intervention_sector_locations.all()]
        )

    def get_sector(self, obj):
        return ",".join(
            [str(x.sector.name)
             for x in obj.intervention_sector_locations.all()]
        )


class InterventionResultExportSerializer(InterventionResultSerializer):
    intervention = serializers.CharField(
        label=_("Reference Number"),
        source="intervention.number",
    )
    country_programme = serializers.CharField(
        label=_("Country Programme"),
        source="cp_output.country_programme.name",
    )
    result_type = serializers.CharField(
        label=_("Result Type"),
        source="cp_output.result_type.name",
    )
    sector = serializers.CharField(
        label=_("Sector"),
        source="cp_output.sector.name",
    )
    name = serializers.CharField(
        label=_("Name"),
        source="cp_output.name",
    )
    code = serializers.CharField(
        label=_("Code"),
        source="cp_output.code",
    )
    from_date = serializers.CharField(
        label=_("From Date"),
        source="cp_output.from_date",
    )
    to_date = serializers.CharField(
        label=_("To Date"),
        source="cp_output.to_date",
    )
    parent = serializers.CharField(
        label=_("Parent"),
        source="cp_output.parent.pk",
    )
    wbs = serializers.CharField(
        label=_("WBS"),
        source="cp_output.wbs",
    )
    vision_id = serializers.CharField(
        label=_("VISION ID"),
        source="cp_output.vision_id",
    )
    gic_code = serializers.CharField(
        label=_("GIC Code"),
        source="cp_output.gic_code",
    )
    gic_name = serializers.CharField(
        label=_("GIC Name"),
        source="cp_output.gic_name",
    )
    sic_code = serializers.CharField(
        label=_("SIC Code"),
        source="cp_output.sic_code",
    )
    sic_name = serializers.CharField(
        label=_("SIC Name"),
        source="cp_output.sic_name",
    )
    activity_focus_code = serializers.CharField(
        label=_("Activity Focus Code"),
        source="cp_output.activity_focus_code",
    )
    activity_focus_name = serializers.CharField(
        label=_("Activity Focus Name"),
        source="cp_output.activity_focus_name",
    )

    class Meta:
        model = InterventionResultLink
        fields = "__all__"


class InterventionResultExportFlatSerializer(InterventionResultExportSerializer):
    parent = serializers.CharField(
        label=_("Parent"),
        source="cp_output.parent.name",
    )

    class Meta:
        model = InterventionResultLink
        fields = "__all__"


class InterventionIndicatorExportSerializer(IndicatorExportSerializer):
    intervention = serializers.SerializerMethodField(
        label=_("Reference Number"),
    )

    def get_intervention(self, obj):
        return ",".join(
            [str(x.intervention.pk)
             for x in obj.interventionresultlink_set.all()]
        )


class InterventionIndicatorExportFlatSerializer(IndicatorExportFlatSerializer):
    intervention = serializers.SerializerMethodField(
        label=_("Reference Number"),
    )

    class Meta:
        model = Indicator
        fields = "__all__"

    def get_intervention(self, obj):
        return ",".join(
            [x.intervention.number
             for x in obj.interventionresultlink_set.all()]
        )


class InterventionExportSerializer(serializers.ModelSerializer):
    # TODO CP Outputs, RAM Indicators, Fund Commitment(s), Supply Plan, Distribution Plan, URL

    partner_name = serializers.CharField(
        label=_("Partner"),
        source='agreement.partner.name',
    )
    partner_type = serializers.CharField(
        label=_("Partner Type"),
        source='agreement.partner.partner_type',
    )
    agreement_number = serializers.CharField(
        label=_("Agreement"),
        source='agreement.agreement_number',
    )
    country_programme = serializers.CharField(
        label=_("Country Programme"),
        source='agreement.country_programme.name',
    )
    offices = serializers.SerializerMethodField(label=_("UNICEF Office"))
    sectors = serializers.SerializerMethodField(label=_("Sectors"))
    locations = serializers.SerializerMethodField(label=_("Locations"))
    fr_numbers = serializers.SerializerMethodField(label=_("FR Number(s)"))
    planned_budget_local = serializers.DecimalField(
        label=_("Total UNICEF Budget (Local)"),
        source='total_unicef_cash_local',
        read_only=True,
        max_digits=20,
        decimal_places=2,
    )
    unicef_budget = serializers.DecimalField(
        label=_("Total UNICEF Budget (USD)"),
        source='total_unicef_budget',
        read_only=True,
        max_digits=20,
        decimal_places=2,
    )
    cso_contribution = serializers.DecimalField(
        label=_("Total CSO Budget (USD)"),
        source='total_partner_contribution',
        read_only=True,
        max_digits=20,
        decimal_places=2,
    )
    partner_contribution_local = serializers.DecimalField(
        label=_("Total CSO Budget (Local)"),
        source='total_partner_contribution_local',
        read_only=True,
        max_digits=20,
        decimal_places=2,
    )
    # unicef_cash_local = serializers.IntegerField(source='total_unicef_cash_local')
    unicef_signatory = serializers.SerializerMethodField(
        label=_("Signed by UNICEF"),
    )
    partner_focal_points = serializers.SerializerMethodField(
        label=_("CSO Authorized Officials"),
    )
    unicef_focal_points = serializers.SerializerMethodField(
        label=_("UNICEF Focal Points"),
    )
    partner_authorized_officer_signatory = serializers.SerializerMethodField(
        label=_("Signed by Partner"),
    )
    cp_outputs = serializers.SerializerMethodField(label=_("CP Outputs"))
    ram_indicators = serializers.SerializerMethodField(
        label=_("RAM Indicators"),
    )
    planned_visits = serializers.SerializerMethodField(
        label=_("Planned Programmatic Visits"),
    )
    spot_checks = serializers.SerializerMethodField(
        label=_("Planned Spot Checks"),
    )
    audit = serializers.SerializerMethodField(label=_("Planned Audits"))
    url = serializers.SerializerMethodField(label=_("URL"))
    days_from_submission_to_signed = serializers.SerializerMethodField(
        label=_("Days from Submission to Signed"),
    )
    days_from_review_to_signed = serializers.SerializerMethodField(
        label=_("Days from Review to Signed"),
    )
    migration_error_msg = serializers.SerializerMethodField(
        label=_("Migration messages"),
    )

    class Meta:
        model = Intervention
        fields = (
            "status",
            "partner_name",
            "partner_type",
            "agreement_number",
            "country_programme",
            "document_type",
            "number",
            "title",
            "start",
            "end",
            "offices",
            "sectors",
            "locations",
            "planned_budget_local",
            "unicef_focal_points",
            "partner_focal_points",
            "population_focus",
            "cp_outputs",
            "ram_indicators",
            "fr_numbers",
            "unicef_budget",
            "cso_contribution",
            "partner_authorized_officer_signatory",
            "partner_contribution_local",
            "planned_visits",
            "spot_checks",
            "audit",
            "submission_date",
            "submission_date_prc",
            "review_date_prc",
            "unicef_signatory",
            "signed_by_unicef_date",
            "migration_error_msg",
            "signed_by_partner_date",
            "url",
            "days_from_submission_to_signed",
            "days_from_review_to_signed"
        )

    def get_unicef_signatory(self, obj):
        return obj.unicef_signatory.get_full_name() if obj.unicef_signatory else ''

    def get_offices(self, obj):
        return ', '.join([o.name for o in obj.offices.all()])

    def get_sectors(self, obj):
        return ', '.join([l.sector.name for l in obj.sector_locations.all()])

    def get_locations(self, obj):
        ll = Location.objects.filter(intervention_sector_locations__intervention=obj.id).order_by('name')
        return ', '.join([l.name for l in ll.all()])

    def get_partner_authorized_officer_signatory(self, obj):
        if obj.partner_authorized_officer_signatory:
            return obj.partner_authorized_officer_signatory.get_full_name()
        else:
            return ''

    def get_partner_focal_points(self, obj):
        return ', '.join([pf.get_full_name() for pf in obj.partner_focal_points.all()])

    def get_unicef_focal_points(self, obj):
        return ', '.join([pf.get_full_name() for pf in obj.unicef_focal_points.all()])

    def get_cp_outputs(self, obj):
        return ', '.join([rs.cp_output.name for rs in obj.result_links.all()])

    def get_ram_indicators(self, obj):
        ram_indicators = []
        for rs in obj.result_links.all():
            if rs.ram_indicators:
                for ram in rs.ram_indicators.all():
                    ram_indicators.append("[{}] {}, ".format(rs.cp_output.name, ram.name))
        return ' '.join([ram for ram in ram_indicators])

    def get_planned_visits(self, obj):
        return ', '.join(['{} ({})'.format(pv.programmatic, pv.year) for pv in obj.planned_visits.all()])

    def get_spot_checks(self, obj):
        return ', '.join(['{} ({})'.format(pv.spot_checks, pv.year) for pv in obj.planned_visits.all()])

    def get_audit(self, obj):
        return ', '.join(['{} ({})'.format(pv.audit, pv.year) for pv in obj.planned_visits.all()])

    def get_url(self, obj):
        return 'https://{}/pmp/interventions/{}/details/'.format(self.context['request'].get_host(), obj.id)

    def get_days_from_submission_to_signed(self, obj):
        return obj.days_from_submission_to_signed

    def get_days_from_review_to_signed(self, obj):
        return obj.days_from_review_to_signed

    def get_fr_numbers(self, obj):
        return ', '.join([x.fr_number for x in obj.frs.all()]) if obj.frs.all().count() > 0 else ""

    def get_migration_error_msg(self, obj):
        return ', '.join([a for a in obj.metadata['error_msg']]) if 'error_msg' in obj.metadata.keys() else ''


class InterventionExportFlatSerializer(InterventionExportSerializer):
    planned_visits = serializers.SerializerMethodField(
        label=_("Planned Programmatic Visits"),
    )
    attachments = serializers.SerializerMethodField(label=_("Attachments"))
    country_programme = serializers.CharField(
        label=_("Country Programme"),
        source='country_programme.name',
    )
    partner_contribution = serializers.CharField(
        label=_("CSO Contribution"),
        source='planned_budget.partner_contribution',
    )
    unicef_cash = serializers.CharField(
        label=_("UNICEF Cash"),
        source='planned_budget.unicef_cash',
    )
    in_kind_amount = serializers.CharField(
        label=_("In Kind Amount"),
        source='planned_budget.in_kind_amount',
    )
    partner_contribution_local = serializers.CharField(
        label=_("CSO Contribution (Local)"),
        source='planned_budget.partner_contribution_local',
    )
    unicef_cash_local = serializers.CharField(
        label=_("UNICEF Cash (Local)"),
        source='planned_budget.unicef_cash_local',
    )
    in_kind_amount_local = serializers.CharField(
        label=_("In Kind Amount (Local)"),
        source='planned_budget.in_kind_amount_local',
    )
    currency = serializers.CharField(
        label=_("Currency"),
        source='planned_budget.currency',
    )
    total = serializers.CharField(
        label=_("Total"),
        source='planned_budget.total',
    )

    class Meta:
        model = Intervention
        fields = "__all__"

    def get_planned_visits(self, obj):
        planned_visits = []
        for planned_visit in obj.planned_visits.all():
            planned_visits.append(
                "Year: {}, Programmatic: {}, Spot Checks: {}, Audit: {}".format(
                    planned_visit.year,
                    planned_visit.programmatic,
                    planned_visit.spot_checks,
                    planned_visit.audit,
                )
            )
        return "\n".join(planned_visits)

    def get_attachments(self, obj):
        return "\n".join(
            ["{}: {}".format(a.type.name, a.attachment.url)
             for a in obj.attachments.all()]
        )
