from django.utils.translation import gettext as _

from rest_framework import serializers

from etools.applications.core.mixins import ExportSerializerMixin
from etools.applications.governments.models import GDD, GDDAmendment, GDDKeyIntervention, GDDResultLink
from etools.applications.governments.serializers.amendments import GDDAmendmentCUSerializer
from etools.applications.partners.serializers.fields import TypeArrayField
from etools.applications.reports.models import Indicator
from etools.applications.reports.serializers.exports import IndicatorExportFlatSerializer, IndicatorExportSerializer
from etools.applications.reports.serializers.v2 import IndicatorSerializer


class GDDExportSerializer(serializers.ModelSerializer):
    # TODO CP Outputs, RAM Indicators, Fund Commitment(s), Supply Plan, Distribution Plan, URL

    partner_name = serializers.CharField(
        label=_("Partner"),
        source='partner.name',
        allow_null=True,
    )
    vendor_number = serializers.CharField(
        label=_("Vendor Number"),
        source='partner.vendor_number',
        allow_null=True,
    )
    partner_type = serializers.CharField(
        label=_("Partner Type"),
        source='partner.partner_type',
        allow_null=True,
    )
    agreement_number = serializers.CharField(
        label=_("Agreement"),
        source='agreement.agreement_number',
        allow_null=True,
    )
    country_programme = serializers.SerializerMethodField(
        label=_("Country Programmes"),
    )
    offices = serializers.SerializerMethodField(label=_("UNICEF Office"))
    sectors = serializers.SerializerMethodField(label=_("Sections"))
    locations = serializers.SerializerMethodField(label=_("Locations"))

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
    planned_visits = serializers.SerializerMethodField(
        label=_("Planned Programmatic Visits"),
    )
    budget_currency = serializers.CharField(
        label=_("Budget Currency"),
        source="planned_budget.currency",
        allow_null=True,
    )
    cso_contribution = serializers.DecimalField(
        label=_("Total Government Contribution"),
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
        label=_("Total GPD Budget"),
        source='total_budget',
        read_only=True,
        max_digits=20,
        decimal_places=2,
    )
    unicef_signatory = serializers.SerializerMethodField(
        label=_("Signed by UNICEF"),
    )
    partner_focal_points = serializers.SerializerMethodField(
        label=_("Government Authorized Officials"),
    )
    unicef_focal_points = serializers.SerializerMethodField(
        label=_("UNICEF Focal Points"),
    )
    partner_authorized_officer_signatory = serializers.SerializerMethodField(
        label=_("Signed by Partner"),
    )
    cp_outputs = serializers.SerializerMethodField(label=_("CP Outputs"))
    url = serializers.SerializerMethodField(label=_("URL"))
    days_from_submission_to_approved = serializers.SerializerMethodField(
        label=_("Days from Submission to Approved"),
    )
    days_from_review_to_approved = serializers.SerializerMethodField(
        label=_("Days from Review to Approved"),
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
        model = GDD
        fields = (
            "partner_name",
            "vendor_number",
            "status",
            "partner_type",
            "agreement_number",
            "country_programme",
            "number",
            "title",
            "start",
            "end",
            "offices",
            "sectors",
            "locations",
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
            "planned_visits",
            "submission_date",
            "submission_date_prc",
            "review_date_prc",
            "partner_authorized_officer_signatory",
            "signed_by_partner_date",
            "unicef_signatory",
            "signed_by_unicef_date",
            "days_from_submission_to_approved",
            "days_from_review_to_approved",
            "amendment_sum",
            "last_amendment_date",
            "attachment_type",
            "total_attachments",
            "cp_outputs",
            "url",
        )

    def get_unicef_signatory(self, obj):
        return obj.unicef_signatory.get_full_name() if obj.unicef_signatory else ''

    def get_country_programme(self, obj):
        return obj.country_programme.name if obj.country_programme else ''

    def get_offices(self, obj):
        return ', '.join([o.name for o in obj.offices.all()])

    def get_sectors(self, obj):
        c_sections = ', '.join([section.name for section in obj.sections.all()])
        if obj.lead_section:
            return f'{obj.lead_section}(Lead Section), {c_sections}'
        return c_sections

    def get_locations(self, obj):
        return ', '.join([loc.name for loc in obj.flat_locations.all()])

    def get_fr_posting_date(self, obj):
        return ', '.join(['{}'.format(f.document_date) for f in obj.frs.all()])

    def get_partner_authorized_officer_signatory(self, obj):
        if obj.partner_authorized_officer_signatory:
            return obj.partner_authorized_officer_signatory.get_full_name()
        return ''

    def get_partner_focal_points(self, obj):
        return ', '.join([pf.get_full_name() for pf in obj.partner_focal_points.all()])

    def get_unicef_focal_points(self, obj):
        return ', '.join([pf.get_full_name() for pf in obj.unicef_focal_points.all()])

    def get_cp_outputs(self, obj):
        return ', '.join([rs.cp_output.cp_output.name for rs in obj.result_links.all() if rs.cp_output])

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
        return 'https://{}/pmp/gdds/{}/details/'.format(self.context['request'].get_host(), obj.id)

    def get_days_from_submission_to_approved(self, obj):
        return obj.days_from_submission_to_approved

    def get_days_from_review_to_approved(self, obj):
        return obj.days_from_review_to_approved

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

    def get_planned_visits(self, obj):
        return ', '.join(['{} (Q1:{} Q2:{}, Q3:{}, Q4:{})'.format(
            pv.year, pv.programmatic_q1, pv.programmatic_q2, pv.programmatic_q3, pv.programmatic_q4
        ) for pv in obj.planned_visits.all()])


class GDDExportFlatSerializer(ExportSerializerMixin, GDDExportSerializer):
    attachments = serializers.SerializerMethodField(label=_("Attachments"))
    country_programme = serializers.CharField(
        label=_("Country Programme"),
        source='country_programme.name',
        read_only=True,
        allow_null=True,
    )
    partner_contribution = serializers.CharField(
        label=_("Government Contribution"),
        source='planned_budget.partner_contribution',
        read_only=True,
        allow_null=True,
    )
    unicef_cash = serializers.CharField(
        label=_("UNICEF Cash"),
        source='planned_budget.unicef_cash',
        read_only=True,
        allow_null=True,
    )
    in_kind_amount = serializers.CharField(
        label=_("In Kind Amount"),
        source='planned_budget.in_kind_amount',
        read_only=True,
        allow_null=True,
    )
    partner_contribution_local = serializers.CharField(
        label=_("Government Contribution (Local)"),
        source='planned_budget.partner_contribution_local',
        read_only=True,
        allow_null=True,
    )
    unicef_cash_local = serializers.CharField(
        label=_("UNICEF Cash (Local)"),
        source='planned_budget.unicef_cash_local',
        read_only=True,
        allow_null=True,
    )
    in_kind_amount_local = serializers.CharField(
        label=_("In Kind Amount (Local)"),
        source='planned_budget.in_kind_amount_local',
        read_only=True,
        allow_null=True,
    )
    currency = serializers.CharField(
        label=_("Currency"),
        source='planned_budget.currency',
        read_only=True,
        allow_null=True,
    )
    total = serializers.CharField(
        label=_("Total"),
        source='planned_budget.total',
        read_only=True,
        allow_null=True,
    )
    planned_visits = serializers.SerializerMethodField(
        label=_("Planned Programmatic Visits"),
    )

    class Meta:
        model = GDD
        fields = "__all__"

    def get_attachments(self, obj):
        return "\n".join(
            ["{}: {}".format(a.type.name, a.attachment.last().url)
             for a in obj.attachments.all()]
        )

    def get_planned_visits(self, obj):
        return ', '.join(['{} (Q1:{} Q2:{}, Q3:{}, Q4:{})'.format(
            pv.year, pv.programmatic_q1, pv.programmatic_q2, pv.programmatic_q3, pv.programmatic_q4
        ) for pv in obj.planned_visits.all()])


class GDDAmendmentExportSerializer(GDDAmendmentCUSerializer):
    types = TypeArrayField(label=_("Types"))

    class Meta:
        model = GDDAmendment
        fields = (
            'id',
            'amendment_number',
            # 'internal_prc_review',
            'created',
            'modified',
            'kind',
            'types',
            'other_description',
            'signed_date',
            'gdd',
            'is_active',
            # signatures
            'signed_by_unicef_date',
            'signed_by_partner_date',
            'unicef_signatory',
            'partner_authorized_officer_signatory',
            'signed_amendment_attachment',
            'difference',
        )


class GDDAmendmentExportFlatSerializer(
    ExportSerializerMixin,
    GDDAmendmentExportSerializer
):
    gdd = serializers.CharField(
        label=_("Reference Number"),
        source="gdd.number",
    )
    unicef_signatory = serializers.SerializerMethodField()
    partner_authorized_officer_signatory = serializers.SerializerMethodField()

    class Meta:
        model = GDDAmendment
        fields = [
            'id',
            'amendment_number',
            # 'internal_prc_review',
            'created',
            'modified',
            'kind',
            'types',
            'other_description',
            'signed_date',
            'gdd',
            'is_active',
            # signatures
            'signed_by_unicef_date',
            'signed_by_partner_date',
            'unicef_signatory',
            'partner_authorized_officer_signatory',
            'signed_amendment_attachment',
            'difference',
        ]

    def get_unicef_signatory(self, obj):
        return obj.unicef_signatory.email if obj.unicef_signatory else ""

    def get_partner_authorized_officer_signatory(self, obj):
        return obj.partner_authorized_officer_signatory.user.email if obj.partner_authorized_officer_signatory else ""


class GDDResultSerializer(serializers.ModelSerializer):
    humanitarian_tag = serializers.SerializerMethodField()
    hidden = serializers.SerializerMethodField()
    ram = serializers.SerializerMethodField()
    ram_indicators = IndicatorSerializer(many=True, read_only=True)

    class Meta:
        model = GDDResultLink
        fields = "__all__"

    def get_humanitarian_tag(self, obj):
        return "Yes" if obj.cp_output.humanitarian_tag else "No"

    def get_hidden(self, obj):
        return "Yes" if obj.cp_output.hidden else "No"

    def get_ram(self, obj):
        return "Yes" if obj.cp_output.ram else "No"


class GDDResultExportSerializer(GDDResultSerializer):
    gdd = serializers.CharField(
        label=_("Reference Number"),
        source="gdd.number",
        read_only=True
    )
    country_programme = serializers.CharField(
        label=_("Country Programme"),
        source="cp_output.country_programme.name",
        read_only=True,
        allow_null=True,
    )
    result_type = serializers.CharField(
        label=_("Result Type"),
        source="cp_output.result_type.name",
        read_only=True
    )
    sector = serializers.CharField(
        label=_("Section"),
        source="cp_output.sector.name",
        read_only=True,
        allow_null=True,
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
        read_only=True,
        allow_null=True,
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
        model = GDDKeyIntervention
        fields = "__all__"


class GDDResultExportFlatSerializer(
        ExportSerializerMixin,
        GDDResultExportSerializer
):
    parent = serializers.CharField(
        label=_("Parent"),
        source="cp_output.parent.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = GDDKeyIntervention
        fields = "__all__"


class GDDAmendmentIndicatorExportSerializer(IndicatorExportSerializer):
    gdd = serializers.SerializerMethodField(
        label=_("Reference Number"),
    )

    def get_gdd(self, obj):
        return ",".join(
            [str(x.gdd.pk)
             for x in obj.gddresultlink_set.all()]
        )


class GDDAmendmentIndicatorExportFlatSerializer(IndicatorExportFlatSerializer):
    gdd = serializers.SerializerMethodField(
        label=_("Reference Number"),
    )

    class Meta:
        model = Indicator
        fields = "__all__"

    def get_gdd(self, obj):
        return ",".join(
            [x.gdd.number
             for x in obj.gddresultlink_set.all()]
        )


class GDDLocationExportSerializer(serializers.Serializer):
    partner = serializers.CharField(source="gdd.partner.name")
    partner_vendor_number = serializers.CharField(source="gdd.partner.vendor_number")
    pd_ref_number = serializers.CharField(source="gdd.number")
    partnership = serializers.CharField(source="gdd.agreement.agreement_number", default='-')
    status = serializers.CharField(source="gdd.status")
    location = serializers.CharField(source="selected_location.name", read_only=True)
    section = serializers.CharField(source="section.name", read_only=True)
    cp_output = serializers.CharField(source="gdd.cp_output_names")
    start = serializers.CharField(source="gdd.start")
    end = serializers.CharField(source="gdd.end")
    focal_point = serializers.CharField(source="gdd.focal_point_names")
    hyperlink = serializers.SerializerMethodField()

    def get_hyperlink(self, obj):
        return 'https://{}/pmp/gdd-interventions/{}/details/'.format(self.context['request'].get_host(), obj.gdd.id)
