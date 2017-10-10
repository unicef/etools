from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers

from funds.serializers import FRsSerializer
from locations.serializers import (
    LocationExportFlatSerializer,
    LocationExportSerializer,
)
from partners.permissions import InterventionPermissions
from partners.serializers.fields import TypeArrayField
from reports.serializers.v1 import SectorLightSerializer
from reports.serializers.v2 import (
    IndicatorExportSerializer,
    IndicatorExportFlatSerializer,
    IndicatorSerializer,
    LowerResultCUSerializer,
    LowerResultSerializer,
)
from locations.models import Location

from partners.models import (
    InterventionBudget,
    InterventionPlannedVisits,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    InterventionSectorLocationLink,
    InterventionResultLink,
)
from reports.models import Indicator, LowerResult
from locations.serializers import LocationLightSerializer
from funds.models import FundsCommitmentItem, FundsReservationHeader


class InterventionBudgetCUSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    partner_contribution = serializers.DecimalField(max_digits=20, decimal_places=2)
    unicef_cash = serializers.DecimalField(max_digits=20, decimal_places=2)
    in_kind_amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    partner_contribution_local = serializers.DecimalField(max_digits=20, decimal_places=2)
    unicef_cash_local = serializers.DecimalField(max_digits=20, decimal_places=2)
    in_kind_amount_local = serializers.DecimalField(max_digits=20, decimal_places=2)

    class Meta:
        model = InterventionBudget
        fields = (
            "id",
            "intervention",
            "partner_contribution",
            "unicef_cash",
            "in_kind_amount",
            "partner_contribution_local",
            "unicef_cash_local",
            "in_kind_amount_local",
            "total",
            'currency'
        )


class InterventionAmendmentCUSerializer(serializers.ModelSerializer):
    amendment_number = serializers.CharField(read_only=True)
    signed_amendment_file = serializers.FileField(source="signed_amendment", read_only=True)

    class Meta:
        model = InterventionAmendment
        fields = "__all__"


class InterventionAmendmentExportSerializer(InterventionAmendmentCUSerializer):
    types = TypeArrayField()

    class Meta:
        model = InterventionAmendment
        fields = "__all__"


class InterventionAmendmentExportFlatSerializer(InterventionAmendmentExportSerializer):
    intervention = serializers.CharField(source="intervention.number")


class PlannedVisitsCUSerializer(serializers.ModelSerializer):
    spot_checks = serializers.IntegerField(read_only=True)
    audit = serializers.IntegerField(read_only=True)

    class Meta:
        model = InterventionPlannedVisits
        fields = "__all__"


class PlannedVisitsNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionPlannedVisits
        fields = (
            "id",
            "year",
            "programmatic",
            "spot_checks",
            "audit",
        )


class InterventionListSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='agreement.partner.name')
    unicef_cash = serializers.DecimalField(source='total_unicef_cash', read_only=True, max_digits=20, decimal_places=2)
    cso_contribution = serializers.DecimalField(source='total_partner_contribution', read_only=True, max_digits=20,
                                                decimal_places=2)
    total_unicef_budget = serializers.DecimalField(read_only=True, max_digits=20, decimal_places=2)
    total_budget = serializers.DecimalField(read_only=True, max_digits=20, decimal_places=2)

    sectors = serializers.SerializerMethodField()
    cp_outputs = serializers.SerializerMethodField()
    offices_names = serializers.SerializerMethodField()
    frs_earliest_start_date = serializers.DateField(source='total_frs.earliest_start_date', read_only=True)
    frs_latest_end_date = serializers.DateField(source='total_frs.latest_end_date', read_only=True)
    frs_total_frs_amt = serializers.DecimalField(source='total_frs.total_frs_amt', read_only=True,
                                                 max_digits=20,
                                                 decimal_places=2)
    frs_total_intervention_amt = serializers.DecimalField(source='total_frs.total_intervention_amt', read_only=True,
                                                          max_digits=20,
                                                          decimal_places=2)
    frs_total_outstanding_amt = serializers.DecimalField(source='total_frs.total_outstanding_amt', read_only=True,
                                                         max_digits=20,
                                                         decimal_places=2)
    actual_amount = serializers.DecimalField(source='total_frs.total_actual_amt', read_only=True,
                                                    max_digits=20,
                                                    decimal_places=2)

    def get_offices_names(self, obj):
        return [o.name for o in obj.offices.all()]

    def get_cp_outputs(self, obj):
        return [rl.cp_output.id for rl in obj.result_links.all()]

    def get_sectors(self, obj):
        return [l.sector.name for l in obj.sector_locations.all()]

    class Meta:
        model = Intervention
        fields = (
            'id', 'number', 'document_type', 'partner_name', 'status', 'title', 'start', 'end', 'frs_total_frs_amt',
            'unicef_cash', 'cso_contribution', 'country_programme', 'frs_earliest_start_date', 'frs_latest_end_date',
            'sectors', 'cp_outputs', 'unicef_focal_points', 'frs_total_intervention_amt', 'frs_total_outstanding_amt',
            'offices', 'actual_amount', 'offices_names', 'total_unicef_budget', 'total_budget', 'metadata',
        )


class MinimalInterventionListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Intervention
        fields = (
            'id',
            'title',
        )


class InterventionLocationSectorNestedSerializer(serializers.ModelSerializer):
    locations = LocationLightSerializer(many=True)
    sector = SectorLightSerializer()

    class Meta:
        model = InterventionSectorLocationLink
        fields = (
            'id', 'sector', 'locations'
        )


class InterventionSectorLocationCUSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionSectorLocationLink
        fields = (
            'id', 'intervention', 'sector', 'locations'
        )


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
        return ",".join([str(x.intervention.pk) for x in obj.intervention_sector_locations.all()])

    def get_sector(self, obj):
        return ",".join([str(x.sector.pk) for x in obj.intervention_sector_locations.all()])


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
        return ",".join([str(x.intervention.number) for x in obj.intervention_sector_locations.all()])

    def get_sector(self, obj):
        return ",".join([str(x.sector.name) for x in obj.intervention_sector_locations.all()])


class InterventionAttachmentSerializer(serializers.ModelSerializer):
    attachment_file = serializers.FileField(source="attachment", read_only=True)

    class Meta:
        model = InterventionAttachment
        fields = (
            'id', 'intervention', 'created', 'type', 'attachment', "attachment_file"
        )


class InterventionResultNestedSerializer(serializers.ModelSerializer):
    # cp_output = ResultLightSerializer()
    # ram_indicators = RAMIndicatorLightSerializer(many=True, read_only=True)
    ll_results = LowerResultSerializer(many=True, read_only=True)

    class Meta:
        model = InterventionResultLink
        fields = (
            'id', 'intervention', 'cp_output', 'ram_indicators', 'll_results'
        )


class InterventionResultCUSerializer(serializers.ModelSerializer):

    lower_results = LowerResultSerializer(many=True, read_only=True)

    class Meta:
        model = InterventionResultLink
        fields = "__all__"

    def update_ll_results(self, instance, ll_results):
        ll_results = ll_results if ll_results else []

        for result in ll_results:
            result['result_link'] = instance.pk
            applied_indicators = {'applied_indicators': result.pop('applied_indicators', [])}
            instance_id = result.get('id', None)
            if instance_id:
                try:
                    ll_result_instance = LowerResult.objects.get(pk=instance_id)
                except LowerResult.DoesNotExist:
                    raise ValidationError('lower_result has an id but cannot be found in the db')

                ll_result_serializer = LowerResultCUSerializer(
                    instance=ll_result_instance,
                    data=result,
                    context=applied_indicators,
                    partial=True
                )

            else:
                ll_result_serializer = LowerResultCUSerializer(data=result, context=applied_indicators)

            if ll_result_serializer.is_valid(raise_exception=True):
                ll_result_serializer.save()

    @transaction.atomic
    def create(self, validated_data):
        ll_results = self.context.pop('ll_results', [])
        instance = super(InterventionResultCUSerializer, self).create(validated_data)
        self.update_ll_results(instance, ll_results)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        ll_results = self.context.pop('ll_results', [])
        self.update_ll_results(instance, ll_results)
        return super(InterventionResultCUSerializer, self).update(instance, validated_data)


class InterventionResultSerializer(serializers.ModelSerializer):
    humanitarian_tag = serializers.SerializerMethodField()
    hidden = serializers.SerializerMethodField()
    ram = serializers.SerializerMethodField()
    ram_indicators = IndicatorSerializer(many=True, read_only=True)

    class Meta:
        model = InterventionResultLink
        fields = "__all__"

    def get_humanitarian_tag(self, obj):
        return "Yes" if obj.cp_output.humanitarian_tag else "No"

    def get_hidden(self, obj):
        return "Yes" if obj.cp_output.hidden else "No"

    def get_ram(self, obj):
        return "Yes" if obj.cp_output.ram else "No"


class InterventionResultExportSerializer(InterventionResultSerializer):
    intervention = serializers.CharField(source="intervention.number")
    country_programme = serializers.CharField(source="cp_output.country_programme.name")
    result_type = serializers.CharField(source="cp_output.result_type.name")
    sector = serializers.CharField(source="cp_output.sector.name")
    name = serializers.CharField(source="cp_output.name")
    code = serializers.CharField(source="cp_output.code")
    from_date = serializers.CharField(source="cp_output.from_date")
    to_date = serializers.CharField(source="cp_output.to_date")
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


class InterventionIndicatorSerializer(serializers.ModelSerializer):
    ram_indicators = IndicatorSerializer(many=True, read_only=True)

    class Meta:
        model = InterventionResultLink
        fields = (
            "intervention",
            "ram_indicators",
        )


class InterventionIndicatorExportSerializer(IndicatorExportSerializer):
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
        return ",".join([str(x.intervention.pk) for x in obj.interventionresultlink_set.all()])


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
        return ",".join([x.intervention.number for x in obj.interventionresultlink_set.all()])


class FundingCommitmentNestedSerializer(serializers.ModelSerializer):
    fc_type = serializers.CharField(source='fund_commitment.fc_type')

    class Meta:
        model = FundsCommitmentItem
        fields = (
            "grant_number",
            "wbs",
            "fc_type",
            "fc_ref_number",
            "commitment_amount",
            "commitment_amount_dc",
        )


class InterventionCreateUpdateSerializer(serializers.ModelSerializer):

    planned_budget = InterventionBudgetCUSerializer(read_only=True)
    partner = serializers.CharField(source='agreement.partner.name', read_only=True)
    prc_review_document_file = serializers.FileField(source='prc_review_document', read_only=True)
    signed_pd_document_file = serializers.FileField(source='signed_pd_document', read_only=True)
    amendments = InterventionAmendmentCUSerializer(many=True, read_only=True, required=False)
    planned_visits = PlannedVisitsNestedSerializer(many=True, read_only=True, required=False)
    attachments = InterventionAttachmentSerializer(many=True, read_only=True, required=False)
    sector_locations = InterventionSectorLocationCUSerializer(many=True, read_only=True, required=False)
    result_links = InterventionResultCUSerializer(many=True, read_only=True, required=False)
    frs = serializers.PrimaryKeyRelatedField(many=True,
                                             queryset=FundsReservationHeader.objects.prefetch_related('intervention')
                                             .all(),
                                             required=False)

    class Meta:
        model = Intervention
        fields = "__all__"

    def to_internal_value(self, data):
        if 'frs' in data:
            if data['frs'] is None:
                data['frs'] = []
        return super(InterventionCreateUpdateSerializer, self).to_internal_value(data)

    def validate_frs(self, frs):
        for fr in frs:
            if fr.intervention:
                if (self.instance is None) or (not self.instance.id) or (fr.intervention.id != self.instance.id):
                    raise ValidationError({'error': 'One or more of the FRs selected is related to a different PD/SSFA,'
                                                    ' {}'.format(fr.fr_number)})
            else:
                # make sure it's not expired
                if fr.expired:
                    raise ValidationError({'error': 'One or more selected FRs is expired,'
                                                    ' {}'.format(fr.fr_number)})
        return frs

    @transaction.atomic
    def update(self, instance, validated_data):
        updated = super(InterventionCreateUpdateSerializer, self).update(instance, validated_data)
        return updated


class InterventionDetailSerializer(serializers.ModelSerializer):
    planned_budget = InterventionBudgetCUSerializer(read_only=True)
    partner = serializers.CharField(source='agreement.partner.name')
    partner_id = serializers.CharField(source='agreement.partner.id', read_only=True)
    prc_review_document_file = serializers.FileField(source='prc_review_document', read_only=True)
    signed_pd_document_file = serializers.FileField(source='signed_pd_document', read_only=True)
    amendments = InterventionAmendmentCUSerializer(many=True, read_only=True, required=False)
    planned_visits = PlannedVisitsNestedSerializer(many=True, read_only=True, required=False)
    sector_locations = InterventionLocationSectorNestedSerializer(many=True, read_only=True, required=False)
    attachments = InterventionAttachmentSerializer(many=True, read_only=True, required=False)
    result_links = InterventionResultNestedSerializer(many=True, read_only=True, required=False)
    submitted_to_prc = serializers.ReadOnlyField()
    frs_details = FRsSerializer(source='frs', read_only=True)
    permissions = serializers.SerializerMethodField(read_only=True)

    def get_permissions(self, obj):
        user = self.context['request'].user
        ps = Intervention.permission_structure()
        permissions = InterventionPermissions(user=user, instance=self.instance, permission_structure=ps)
        return permissions.get_permissions()

    class Meta:
        model = Intervention
        fields = (
            "id", 'frs', "partner", "agreement", "document_type", "number", "prc_review_document_file", "frs_details",
            "signed_pd_document_file", "title", "status", "start", "end", "submission_date_prc", "review_date_prc",
            "submission_date", "prc_review_document", "submitted_to_prc", "signed_pd_document", "signed_by_unicef_date",
            "unicef_signatory", "unicef_focal_points", "partner_focal_points", "partner_authorized_officer_signatory",
            "offices", "planned_visits", "population_focus", "sector_locations", "signed_by_partner_date",
            "created", "modified", "planned_budget", "result_links", 'country_programme', 'metadata', 'contingency_pd',
            "amendments", "planned_visits", "attachments", 'permissions', 'partner_id',
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
            "status", "partner_name", "partner_type", "agreement_number", "country_programme", "document_type", "number",
            "title", "start", "end", "offices", "sectors", "locations", "planned_budget_local", "unicef_focal_points",
            "partner_focal_points", "population_focus", "cp_outputs", "ram_indicators", "fr_numbers",
            "unicef_budget", "cso_contribution", "partner_authorized_officer_signatory",
            "partner_contribution_local", "planned_visits", "spot_checks", "audit", "submission_date",
            "submission_date_prc", "review_date_prc", "unicef_signatory", "signed_by_unicef_date",
            "migration_error_msg",
            "signed_by_partner_date", "url", "days_from_submission_to_signed", "days_from_review_to_signed"
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
        return "\n".join(["{}: {}".format(a.type.name, a.attachment.url) for a in obj.attachments.all()])


class InterventionSummaryListSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='agreement.partner.name')
    unicef_cash = serializers.DecimalField(source='total_unicef_cash', read_only=True, max_digits=20, decimal_places=2)
    cso_contribution = serializers.DecimalField(source='total_partner_contribution', read_only=True, max_digits=20,
                                                decimal_places=2)
    total_unicef_budget = serializers.DecimalField(read_only=True, max_digits=20, decimal_places=2)
    total_budget = serializers.DecimalField(read_only=True, max_digits=20, decimal_places=2)

    sectors = serializers.SerializerMethodField()
    cp_outputs = serializers.SerializerMethodField()
    offices_names = serializers.SerializerMethodField()
    frs_earliest_start_date = serializers.DateField(source='total_frs.earliest_start_date', read_only=True)
    frs_latest_end_date = serializers.DateField(source='total_frs.latest_end_date', read_only=True)
    frs_total_frs_amt = serializers.DecimalField(source='total_frs.total_frs_amt', read_only=True,
                                                 max_digits=20,
                                                 decimal_places=2)
    frs_total_intervention_amt = serializers.DecimalField(source='total_frs.total_intervention_amt', read_only=True,
                                                          max_digits=20,
                                                          decimal_places=2)
    frs_total_outstanding_amt = serializers.DecimalField(source='total_frs.total_outstanding_amt', read_only=True,
                                                         max_digits=20,
                                                         decimal_places=2)
    actual_amount = serializers.DecimalField(source='total_frs.total_actual_amt', read_only=True,
                                                    max_digits=20,
                                                    decimal_places=2)

    def get_offices_names(self, obj):
        return [o.name for o in obj.offices.all()]

    def get_cp_outputs(self, obj):
        return [rl.cp_output.id for rl in obj.result_links.all()]

    def get_sectors(self, obj):
        return [l.sector.name for l in obj.sector_locations.all()]

    class Meta:
        model = Intervention
        fields = (
            'id', 'number', 'partner_name', 'status', 'title', 'start', 'end', 'unicef_cash', 'cso_contribution',
            'total_unicef_budget',
            'total_budget', 'sectors', 'cp_outputs', 'offices_names', 'frs_earliest_start_date', 'frs_latest_end_date',
            'frs_total_frs_amt', 'frs_total_intervention_amt', 'frs_total_outstanding_amt', 'actual_amount'
        )


class InterventionLocationSectorMapNestedSerializer(serializers.ModelSerializer):
    sector = SectorLightSerializer()

    class Meta:
        model = InterventionSectorLocationLink
        fields = (
            'id', 'sector', 'locations'
        )


class InterventionListMapSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='agreement.partner.name')
    partner_id = serializers.CharField(source='agreement.partner.id')
    sector_locations = InterventionLocationSectorMapNestedSerializer(many=True, read_only=True, required=False)

    class Meta:
        model = Intervention
        fields = (
            "id", "partner_id", "partner_name", "agreement", "document_type", "number", "title", "status",
            "start", "end",
            "offices", "sector_locations",
        )
