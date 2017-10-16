from __future__ import unicode_literals

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
)


class InterventionAmendmentExportSerializer(InterventionAmendmentCUSerializer):
    types = TypeArrayField()

    class Meta:
        model = InterventionAmendment
        fields = "__all__"


class InterventionAmendmentExportFlatSerializer(InterventionAmendmentExportSerializer):
    intervention = serializers.CharField(source="intervention.number")


class InterventionSectorLocationLinkExportSerializer(LocationExportSerializer):
    intervention = serializers.SerializerMethodField()
    sector = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = (
            'intervention',
            'sector',
            'name',
            'location_type',
            'p_code',
            'geom',
            'point',
            'latitude',
            'longitude',
        )

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
    intervention = serializers.SerializerMethodField()
    sector = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = (
            'id',
            'intervention',
            'sector',
            'name',
            'location_type',
            'p_code',
            'geom',
            'point',
            'latitude',
            'longitude',
        )

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
    intervention = serializers.CharField(source="intervention.number")
    country_programme = serializers.CharField(source="cp_output.country_programme.name")
    result_type = serializers.CharField(source="cp_output.result_type.name")
    sector = serializers.CharField(source="cp_output.sector.name")
    name = serializers.CharField(source="cp_output.name")
    code = serializers.CharField(source="cp_output.code")
    from_date = serializers.CharField(source="cp_output.from_date")
    to_date = serializers.CharField(source="cp_output.to_date")
    parent = serializers.CharField(source="cp_output.parent.pk")
    wbs = serializers.CharField(source="cp_output.wbs")
    vision_id = serializers.CharField(source="cp_output.vision_id")
    gic_code = serializers.CharField(source="cp_output.gic_code")
    gic_name = serializers.CharField(source="cp_output.gic_name")
    sic_code = serializers.CharField(source="cp_output.sic_code")
    sic_name = serializers.CharField(source="cp_output.sic_name")
    activity_focus_code = serializers.CharField(source="cp_output.activity_focus_code")
    activity_focus_name = serializers.CharField(source="cp_output.activity_focus_name")

    class Meta:
        model = InterventionResultLink
        fields = (
            "intervention",
            "country_programme",
            "result_type",
            "sector",
            "name",
            "code",
            "from_date",
            "to_date",
            "parent",
            "humanitarian_tag",
            "wbs",
            "vision_id",
            "gic_code",
            "gic_name",
            "sic_code",
            "sic_name",
            "activity_focus_code",
            "activity_focus_name",
            "hidden",
            "ram",
        )


class InterventionResultExportFlatSerializer(InterventionResultExportSerializer):
    parent = serializers.CharField(source="cp_output.parent.name")

    class Meta:
        model = InterventionResultLink
        fields = (
            "id",
            "intervention",
            "country_programme",
            "result_type",
            "sector",
            "name",
            "code",
            "from_date",
            "to_date",
            "parent",
            "humanitarian_tag",
            "wbs",
            "vision_id",
            "gic_code",
            "gic_name",
            "sic_code",
            "sic_name",
            "activity_focus_code",
            "activity_focus_name",
            "hidden",
            "ram",
        )


class InterventionIndicatorExportSerializer(serializers.ModelSerializer):
    intervention = serializers.SerializerMethodField()

    class Meta:
        model = Indicator
        fields = (
            "intervention",
            "sector",
            "result",
            "name",
            "code",
            "unit",
            "total",
            "sector_total",
            "current",
            "sector_current",
            "assumptions",
            "target",
            "baseline",
            "ram_indicator",
            "active",
            "view_on_dashboard",
        )

    def get_intervention(self, obj):
        return ",".join(
            [str(x.intervention.pk)
             for x in obj.interventionresultlink_set.all()]
        )


class InterventionIndicatorExportFlatSerializer(IndicatorExportFlatSerializer):
    intervention = serializers.SerializerMethodField()

    class Meta:
        model = Indicator
        fields = (
            "id",
            "intervention",
            "sector",
            "result",
            "name",
            "code",
            "unit",
            "total",
            "sector_total",
            "current",
            "sector_current",
            "assumptions",
            "target",
            "baseline",
            "ram_indicator",
            "active",
            "view_on_dashboard",
        )

    def get_intervention(self, obj):
        return ",".join(
            [x.intervention.number
             for x in obj.interventionresultlink_set.all()]
        )


class InterventionExportSerializer(serializers.ModelSerializer):
    # TODO CP Outputs, RAM Indicators, Fund Commitment(s), Supply Plan, Distribution Plan, URL

    partner_name = serializers.CharField(source='agreement.partner.name')
    partner_type = serializers.CharField(source='agreement.partner.partner_type')
    agreement_number = serializers.CharField(source='agreement.agreement_number')
    country_programme = serializers.CharField(source='agreement.country_programme.name')
    offices = serializers.SerializerMethodField()
    sectors = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    fr_numbers = serializers.SerializerMethodField()
    planned_budget_local = serializers.DecimalField(
        source='total_unicef_cash_local',
        read_only=True,
        max_digits=20,
        decimal_places=2)
    unicef_budget = serializers.DecimalField(
        source='total_unicef_budget',
        read_only=True,
        max_digits=20,
        decimal_places=2)
    cso_contribution = serializers.DecimalField(
        source='total_partner_contribution',
        read_only=True,
        max_digits=20,
        decimal_places=2)
    partner_contribution_local = serializers.DecimalField(
        source='total_partner_contribution_local',
        read_only=True,
        max_digits=20,
        decimal_places=2)
    # unicef_cash_local = serializers.IntegerField(source='total_unicef_cash_local')
    unicef_signatory = serializers.SerializerMethodField()
    partner_focal_points = serializers.SerializerMethodField()
    unicef_focal_points = serializers.SerializerMethodField()
    partner_authorized_officer_signatory = serializers.SerializerMethodField()
    cp_outputs = serializers.SerializerMethodField()
    ram_indicators = serializers.SerializerMethodField()
    planned_visits = serializers.SerializerMethodField()
    spot_checks = serializers.SerializerMethodField()
    audit = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    days_from_submission_to_signed = serializers.SerializerMethodField()
    days_from_review_to_signed = serializers.SerializerMethodField()
    migration_error_msg = serializers.SerializerMethodField()

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
    planned_visits = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    country_programme = serializers.CharField(source='country_programme.name')
    partner_contribution = serializers.CharField(source='planned_budget.partner_contribution')
    unicef_cash = serializers.CharField(source='planned_budget.unicef_cash')
    in_kind_amount = serializers.CharField(source='planned_budget.in_kind_amount')
    partner_contribution_local = serializers.CharField(source='planned_budget.partner_contribution_local')
    unicef_cash_local = serializers.CharField(source='planned_budget.unicef_cash_local')
    in_kind_amount_local = serializers.CharField(source='planned_budget.in_kind_amount_local')
    currency = serializers.CharField(source='planned_budget.currency')
    total = serializers.CharField(source='planned_budget.total')

    class Meta:
        model = Intervention
        fields = (
            "id",
            "document_type",
            "number",
            "country_programme",
            "title",
            "status",
            "start",
            "end",
            "submission_date",
            "submission_date_prc",
            "review_date_prc",
            "prc_review_document",
            "signed_by_unicef_date",
            "signed_by_partner_date",
            "fr_numbers",
            "population_focus",
            "agreement_number",
            "partner_authorized_officer_signatory",
            "unicef_signatory",
            "signed_pd_document",
            "unicef_focal_points",
            "partner_focal_points",
            "offices",
            "planned_visits",
            "partner_contribution",
            "unicef_cash",
            "in_kind_amount",
            "partner_contribution_local",
            "unicef_cash_local",
            "in_kind_amount_local",
            "currency",
            "total",
            "attachments",
            "created",
            "modified",
        )

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
