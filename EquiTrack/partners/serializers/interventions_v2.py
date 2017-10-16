from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers

from funds.models import FundsCommitmentItem, FundsReservationHeader
from funds.serializers import FRsSerializer
from locations.serializers import LocationLightSerializer
from partners.permissions import InterventionPermissions
from partners.models import (
    InterventionBudget,
    InterventionPlannedVisits,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    InterventionSectorLocationLink,
    InterventionResultLink,
)
from reports.models import LowerResult
from reports.serializers.v1 import SectorLightSerializer
from reports.serializers.v2 import (
    IndicatorSerializer,
    LowerResultCUSerializer,
    LowerResultSerializer,
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
            "total",
            'currency'
        )


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


class InterventionIndicatorSerializer(serializers.ModelSerializer):
    ram_indicators = IndicatorSerializer(many=True, read_only=True)

    class Meta:
        model = InterventionResultLink
        fields = (
            "intervention",
            "ram_indicators",
        )


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
