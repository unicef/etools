from django.utils.translation import ugettext as _

from rest_framework import serializers

from etools.applications.EquiTrack.mixins import ExportSerializerMixin
from etools.applications.locations.models import Location
from etools.applications.locations.serializers import LocationExportFlatSerializer, LocationExportSerializer
from etools.applications.partners.models import Intervention, InterventionAmendment, InterventionResultLink
from etools.applications.partners.serializers.fields import TypeArrayField
from etools.applications.partners.serializers.interventions_v2 import (InterventionAmendmentCUSerializer,
                                                                       InterventionResultSerializer,)
from etools.applications.reports.models import Indicator
from etools.applications.reports.serializers.exports import IndicatorExportFlatSerializer, IndicatorExportSerializer


class InterventionAmendmentExportSerializer(InterventionAmendmentCUSerializer):
    types = TypeArrayField(label=_("Types"))

    class Meta:
        model = InterventionAmendment
        exclude = ("signed_amendment_attachment", )


class InterventionAmendmentExportFlatSerializer(
        ExportSerializerMixin,
        InterventionAmendmentExportSerializer
):
    intervention = serializers.CharField(
        label=_("Reference Number"),
        source="intervention.number",
    )

    class Meta:
        model = InterventionAmendment
        exclude = ("signed_amendment_attachment", )


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


class InterventionSectorLocationLinkExportFlatSerializer(
        ExportSerializerMixin,
        LocationExportFlatSerializer
):
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
        read_only=True
    )
    country_programme = serializers.CharField(
        label=_("Country Programme"),
        source="cp_output.country_programme.name",
        read_only=True
    )
    result_type = serializers.CharField(
        label=_("Result Type"),
        source="cp_output.result_type.name",
        read_only=True
    )
    sector = serializers.CharField(
        label=_("Sector"),
        source="cp_output.sector.name",
        read_only=True
    )
    name = serializers.CharField(
        label=_("Name"),
        source="cp_output.name",
        read_only=True
    )
    code = serializers.CharField(
        label=_("Code"),
        source="cp_output.code",
        read_only=True
    )
    from_date = serializers.CharField(
        label=_("From Date"),
        source="cp_output.from_date",
        read_only=True
    )
    to_date = serializers.CharField(
        label=_("To Date"),
        source="cp_output.to_date",
        read_only=True
    )
    parent = serializers.CharField(
        label=_("Parent"),
        source="cp_output.parent.pk",
        read_only=True
    )
    wbs = serializers.CharField(
        label=_("WBS"),
        source="cp_output.wbs",
        read_only=True
    )
    vision_id = serializers.CharField(
        label=_("VISION ID"),
        source="cp_output.vision_id",
        read_only=True
    )
    gic_code = serializers.CharField(
        label=_("GIC Code"),
        source="cp_output.gic_code",
        read_only=True
    )
    gic_name = serializers.CharField(
        label=_("GIC Name"),
        source="cp_output.gic_name",
        read_only=True
    )
    sic_code = serializers.CharField(
        label=_("SIC Code"),
        source="cp_output.sic_code",
        read_only=True
    )
    sic_name = serializers.CharField(
        label=_("SIC Name"),
        source="cp_output.sic_name",
        read_only=True
    )
    activity_focus_code = serializers.CharField(
        label=_("Activity Focus Code"),
        source="cp_output.activity_focus_code",
        read_only=True
    )
    activity_focus_name = serializers.CharField(
        label=_("Activity Focus Name"),
        source="cp_output.activity_focus_name",
        read_only=True
    )

    class Meta:
        model = InterventionResultLink
        fields = "__all__"


class InterventionResultExportFlatSerializer(
        ExportSerializerMixin,
        InterventionResultExportSerializer
):
    parent = serializers.CharField(
        label=_("Parent"),
        source="cp_output.parent.name",
        read_only=True
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
    vendor_number = serializers.CharField(
        label=_("Vendor #"),
        source='agreement.partner.vendor_number',
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
        source='country_programme.name',
    )
    offices = serializers.SerializerMethodField(label=_("UNICEF Office"))
    sectors = serializers.SerializerMethodField(label=_("Sections"))
    locations = serializers.SerializerMethodField(label=_("Locations"))
    contingency_pd = serializers.SerializerMethodField(label=_("Contingency PD"))
    intervention_clusters = serializers.SerializerMethodField(
        label=_("Cluster"),
    )
    fr_numbers = serializers.SerializerMethodField(label=_("FR Number(s)"))
    fr_currency = serializers.SerializerMethodField(label=_("FR Currency"))
    fr_posting_date = serializers.SerializerMethodField(label=_("FR Posting Date"))
    fr_amount = serializers.SerializerMethodField(
        label=_("FR Amount"),
    )
    fr_actual_amount = serializers.SerializerMethodField(
        label=_("FR Actual CT"),
    )
    fr_outstanding_amt = serializers.SerializerMethodField(
        label=_("Outstanding DCT"),
    )
    budget_currency = serializers.CharField(
        label=_("Budget Currency"),
        source="planned_budget.currency"
    )
    cso_contribution = serializers.DecimalField(
        label=_("Total CSO Contribution"),
        source='total_partner_contribution',
        read_only=True,
        max_digits=20,
        decimal_places=2,
    )
    unicef_budget = serializers.DecimalField(
        label=_("UNICEF Cash"),
        source='total_unicef_cash',
        read_only=True,
        max_digits=20,
        decimal_places=2,
    )
    unicef_supply = serializers.DecimalField(
        label=_("UNICEF Supply"),
        source='total_in_kind_amount',
        read_only=True,
        max_digits=20,
        decimal_places=2,
    )
    total_planned_budget = serializers.DecimalField(
        label=_("Total PD/SSFA Budget"),
        source='total_budget',
        read_only=True,
        max_digits=20,
        decimal_places=2,
    )
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
    url = serializers.SerializerMethodField(label=_("URL"))
    days_from_submission_to_signed = serializers.SerializerMethodField(
        label=_("Days from Submission to Signed"),
    )
    days_from_review_to_signed = serializers.SerializerMethodField(
        label=_("Days from Review to Signed"),
    )
    amendment_sum = serializers.SerializerMethodField(
        label=_("Total no. of amendments"),
    )
    last_amendment_date = serializers.SerializerMethodField(
        label=_("Last amendment date"),
    )
    attachment_type = serializers.SerializerMethodField(
        label=_("Attachment type"),
    )
    total_attachments = serializers.SerializerMethodField(
        label=_("# of attachments"),
    )

    class Meta:
        model = Intervention
        fields = (
            "partner_name",
            "vendor_number",
            "status",
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
            "contingency_pd",
            "intervention_clusters",
            "unicef_focal_points",
            "partner_focal_points",
            "budget_currency",
            "cso_contribution",
            "unicef_budget",
            "unicef_supply",
            "total_planned_budget",
            "fr_numbers",
            "fr_currency",
            "fr_posting_date",
            "fr_amount",
            "fr_actual_amount",
            "fr_outstanding_amt",
            "submission_date",
            "submission_date_prc",
            "review_date_prc",
            "partner_authorized_officer_signatory",
            "signed_by_partner_date",
            "unicef_signatory",
            "signed_by_unicef_date",
            "days_from_submission_to_signed",
            "days_from_review_to_signed",
            "amendment_sum",
            "last_amendment_date",
            "attachment_type",
            "total_attachments",
            "cp_outputs",
            "url",
        )

    def get_unicef_signatory(self, obj):
        return obj.unicef_signatory.get_full_name() if obj.unicef_signatory else ''

    def get_offices(self, obj):
        return ', '.join([o.name for o in obj.offices.all()])

    def get_sectors(self, obj):
        return ', '.join([s.name for s in obj.sections.all()])

    def get_intervention_clusters(self, obj):
        return ', '.join([c for c in obj.intervention_clusters()])

    def get_contingency_pd(self, obj):
        return "Yes" if obj.contingency_pd else "No"

    def get_locations(self, obj):
        return ', '.join([l.name for l in obj.flat_locations.all()])

    def get_fr_posting_date(self, obj):
        return ', '.join(['{}'.format(f.document_date) for f in obj.frs.all()])

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

    def fr_currencies_ok(self, obj):
        return obj.frs__currency__count == 1 if obj.frs__currency__count else None

    def get_fr_currency(self, obj):
        return obj.max_fr_currency if self.fr_currencies_ok(obj) else ''

    def get_fr_amount(self, obj):
        return obj.frs__total_amt_local__sum

    def get_fr_actual_amount(self, obj):
        return 'Error: Multi-currency Transaction' if obj.multi_curr_flag else obj.frs__actual_amt_local__sum

    def get_fr_outstanding_amt(self, obj):
        return obj.frs__outstanding_amt_local__sum

    def get_url(self, obj):
        return 'https://{}/pmp/interventions/{}/details/'.format(self.context['request'].get_host(), obj.id)

    def get_days_from_submission_to_signed(self, obj):
        return obj.days_from_submission_to_signed

    def get_days_from_review_to_signed(self, obj):
        return obj.days_from_review_to_signed

    def get_fr_numbers(self, obj):
        return ', '.join([x.fr_number for x in obj.frs.all()]) if obj.frs.count() > 0 else ""

    def get_amendment_sum(self, obj):
        return obj.amendments.count()

    def get_last_amendment_date(self, obj):
        return '{}'.format(obj.amendments.order_by('-signed_date').values_list('signed_date', flat=True)[0]) \
            if obj.amendments.count() > 0 else ''

    def get_attachment_type(self, obj):
        return ', '.join(['{}'.format(att.type.name) for att in obj.attachments.all()])

    def get_total_attachments(self, obj):
        return obj.attachments.count()


class InterventionExportFlatSerializer(ExportSerializerMixin, InterventionExportSerializer):
    attachments = serializers.SerializerMethodField(label=_("Attachments"))
    country_programme = serializers.CharField(
        label=_("Country Programme"),
        source='country_programme.name',
        read_only=True
    )
    partner_contribution = serializers.CharField(
        label=_("CSO Contribution"),
        source='planned_budget.partner_contribution',
        read_only=True
    )
    unicef_cash = serializers.CharField(
        label=_("UNICEF Cash"),
        source='planned_budget.unicef_cash',
        read_only=True
    )
    in_kind_amount = serializers.CharField(
        label=_("In Kind Amount"),
        source='planned_budget.in_kind_amount',
        read_only=True
    )
    partner_contribution_local = serializers.CharField(
        label=_("CSO Contribution (Local)"),
        source='planned_budget.partner_contribution_local',
        read_only=True
    )
    unicef_cash_local = serializers.CharField(
        label=_("UNICEF Cash (Local)"),
        source='planned_budget.unicef_cash_local',
        read_only=True
    )
    in_kind_amount_local = serializers.CharField(
        label=_("In Kind Amount (Local)"),
        source='planned_budget.in_kind_amount_local',
        read_only=True
    )
    currency = serializers.CharField(
        label=_("Currency"),
        source='planned_budget.currency',
        read_only=True
    )
    total = serializers.CharField(
        label=_("Total"),
        source='planned_budget.total',
        read_only=True
    )

    class Meta:
        model = Intervention
        fields = "__all__"

    def get_attachments(self, obj):
        return "\n".join(
            ["{}: {}".format(a.type.name, a.attachment.url)
             for a in obj.attachments.all()]
        )
