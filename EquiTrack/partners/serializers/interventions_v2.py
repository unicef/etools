from __future__ import unicode_literals
import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from reports.serializers.v1 import SectorLightSerializer
from reports.serializers.v2 import LowerResultSerializer, LowerResultCUSerializer
from locations.models import Location

from partners.models import (
    InterventionBudget,
    SupplyPlan,
    DistributionPlan,
    InterventionPlannedVisits,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    InterventionSectorLocationLink,
    InterventionResultLink,
)
from reports.models import LowerResult
from locations.serializers import LocationLightSerializer
from funds.models import FundsCommitmentItem


class InterventionBudgetNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionBudget
        fields = (
            "id",
            "partner_contribution",
            "unicef_cash",
            "in_kind_amount",
            "partner_contribution_local",
            "unicef_cash_local",
            "in_kind_amount_local",
            "year",
            "total",
            "currency"
        )


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
            "year",
            "total",
            'currency'
        )
        # read_only_fields = [u'total']

    def validate(self, data):
        errors = {}
        try:
            data = super(InterventionBudgetCUSerializer, self).validate(data)
        except ValidationError as e:
            errors.update(e)

        year = data.get("year", "")
        # To avoid any confusion.. budget year will always be required
        if not year:
            errors.update(year="Budget year is required")

        if errors:
            raise serializers.ValidationError(errors)

        return data


class SupplyPlanCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = SupplyPlan
        fields = "__all__"


class SupplyPlanNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = SupplyPlan
        fields = (
            'id',
            "item",
            "quantity",
        )


class DistributionPlanCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = DistributionPlan
        fields = "__all__"


class DistributionPlanNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = DistributionPlan
        fields = "__all__"


class InterventionAmendmentCUSerializer(serializers.ModelSerializer):
    amendment_number = serializers.CharField(read_only=True)
    signed_amendment_file = serializers.FileField(source="signed_amendment", read_only=True)

    class Meta:
        model = InterventionAmendment
        fields = "__all__"


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

    unicef_budget = serializers.IntegerField(source='total_unicef_cash')
    cso_contribution = serializers.IntegerField(source='total_partner_contribution')
    sectors = serializers.SerializerMethodField()
    cp_outputs = serializers.SerializerMethodField()

    def get_cp_outputs(self, obj):
        return [rl.cp_output.id for rl in obj.result_links.all()]

    def get_sectors(self, obj):
        return [l.sector.name for l in obj.sector_locations.all()]

    class Meta:
        model = Intervention
        fields = (
            'id', 'number', 'hrp', 'document_type', 'partner_name', 'status', 'title', 'start', 'end',
            'unicef_budget', 'cso_contribution',
            'sectors', 'cp_outputs', 'unicef_focal_points',
            'offices'
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


class InterventionAttachmentSerializer(serializers.ModelSerializer):
    attachment_file = serializers.FileField(source="attachment", read_only=True)

    class Meta:
        model = InterventionAttachment
        fields = (
            'id', 'intervention', 'type', 'attachment', "attachment_file"
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

    planned_budget = InterventionBudgetNestedSerializer(many=True, read_only=True)
    partner = serializers.CharField(source='agreement.partner.name', read_only=True)
    prc_review_document_file = serializers.FileField(source='prc_review_document', read_only=True)
    signed_pd_document_file = serializers.FileField(source='signed_pd_document', read_only=True)
    supplies = SupplyPlanCreateUpdateSerializer(many=True, read_only=True, required=False)
    distributions = DistributionPlanCreateUpdateSerializer(many=True, read_only=True, required=False)
    amendments = InterventionAmendmentCUSerializer(many=True, read_only=True, required=False)
    planned_visits = PlannedVisitsNestedSerializer(many=True, read_only=True, required=False)
    attachments = InterventionAttachmentSerializer(many=True, read_only=True, required=False)
    sector_locations = InterventionSectorLocationCUSerializer(many=True, read_only=True, required=False)
    result_links = InterventionResultCUSerializer(many=True, read_only=True, required=False)

    class Meta:
        model = Intervention
        fields = "__all__"

    @transaction.atomic
    def update(self, instance, validated_data):
        updated = super(InterventionCreateUpdateSerializer, self).update(instance, validated_data)
        return updated


class InterventionDetailSerializer(serializers.ModelSerializer):
    planned_budget = InterventionBudgetNestedSerializer(many=True, read_only=True)
    partner = serializers.CharField(source='agreement.partner.name')
    prc_review_document_file = serializers.FileField(source='prc_review_document', read_only=True)
    signed_pd_document_file = serializers.FileField(source='signed_pd_document', read_only=True)
    supplies = SupplyPlanNestedSerializer(many=True, read_only=True, required=False)
    distributions = DistributionPlanNestedSerializer(many=True, read_only=True, required=False)
    amendments = InterventionAmendmentCUSerializer(many=True, read_only=True, required=False)
    planned_visits = PlannedVisitsNestedSerializer(many=True, read_only=True, required=False)
    sector_locations = InterventionLocationSectorNestedSerializer(many=True, read_only=True, required=False)
    attachments = InterventionAttachmentSerializer(many=True, read_only=True, required=False)
    result_links = InterventionResultNestedSerializer(many=True, read_only=True, required=False)
    fr_numbers_details = serializers.SerializerMethodField(read_only=True, required=False)
    submitted_to_prc = serializers.ReadOnlyField()

    def get_fr_numbers_details(self, obj):
        data = {}
        if obj.fr_numbers:
            data = {k: [] for k in obj.fr_numbers}
            try:
                fc_items = FundsCommitmentItem.objects.filter(
                    fr_number__in=obj.fr_numbers).select_related('fund_commitment')
            except FundsCommitmentItem.DoesNotExist:
                pass
            else:
                for fc in fc_items:
                    serializer = FundingCommitmentNestedSerializer(fc)
                    data[fc.fr_number].append(serializer.data)
        return data

    class Meta:
        model = Intervention
        fields = (
            "id", "partner", "agreement", "document_type", "hrp", "number", "prc_review_document_file",
            "signed_pd_document_file", "title", "status", "start", "end", "submission_date_prc", "review_date_prc",
            "submission_date", "prc_review_document", "submitted_to_prc", "signed_pd_document", "signed_by_unicef_date",
            "unicef_signatory", "unicef_focal_points", "partner_focal_points", "partner_authorized_officer_signatory",
            "offices", "fr_numbers", "planned_visits", "population_focus", "sector_locations", "signed_by_partner_date",
            "created", "modified", "planned_budget", "result_links",
            "amendments", "planned_visits", "attachments", "supplies", "distributions", "fr_numbers_details",
        )


class InterventionExportSerializer(serializers.ModelSerializer):

    # TODO CP Outputs, RAM Indicators, Fund Commitment(s), Supply Plan, Distribution Plan, URL

    partner_name = serializers.CharField(source='agreement.partner.name')
    partner_type = serializers.CharField(source='agreement.partner.partner_type')
    agreement_name = serializers.CharField(source='agreement.agreement_number')
    country_programme = serializers.CharField(source='agreement.country_programme.name')
    offices = serializers.SerializerMethodField()
    sectors = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    fr_numbers = serializers.SerializerMethodField()
    local_currency = serializers.SerializerMethodField()
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
    hrp_name = serializers.CharField(source='hrp.name')
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

    class Meta:
        model = Intervention
        fields = (
            "status", "partner_name", "partner_type", "agreement_name", "country_programme", "document_type", "number", "title",
            "start", "end", "offices", "sectors", "locations", "planned_budget_local", "unicef_focal_points",
            "partner_focal_points", "population_focus", "hrp_name", "cp_outputs", "ram_indicators", "fr_numbers", "local_currency",
            "unicef_budget", "cso_contribution", "partner_authorized_officer_signatory",
            "partner_contribution_local", "planned_visits", "spot_checks", "audit", "submission_date",
            "submission_date_prc", "review_date_prc", "unicef_signatory", "signed_by_unicef_date",
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
        return obj.partner_authorized_officer_signatory.get_full_name() if obj.partner_authorized_officer_signatory else ''

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
                    ram_indicators.append("{}, ".format(ram.name))

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

    def get_local_currency(self, obj):
        planned_budget = obj.planned_budget.first()
        return planned_budget.currency if planned_budget else ""

    def get_fr_numbers(self, obj):
        return ', '.join([x for x in obj.fr_numbers]) if obj.fr_numbers else ""


class InterventionSummaryListSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='agreement.partner.name')
    planned_budget = serializers.SerializerMethodField()

    def get_planned_budget(self, obj):
        year = datetime.datetime.now().year
        return obj.planned_budget.filter(year=year).aggregate(
            total=Sum('unicef_cash'))['total'] or 0

    class Meta:
        model = Intervention
        fields = (
            'id', 'number', 'partner_name', 'status', 'title', 'start', 'end', 'planned_budget'
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
            "id", "partner_id", "partner_name", "agreement", "document_type", "hrp", "number", "title", "status", "start", "end",
            "offices", "sector_locations",
        )
