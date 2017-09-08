from __future__ import unicode_literals

from rest_framework import serializers
from rest_framework.renderers import JSONRenderer

from funds.serializers import FRsSerializer
from partners.permissions import InterventionPermissions
from partners.serializers.interventions_v2 import InterventionBudgetCUSerializer, SupplyPlanNestedSerializer, \
    DistributionPlanNestedSerializer, InterventionAmendmentCUSerializer, PlannedVisitsNestedSerializer, \
    InterventionLocationSectorNestedSerializer, InterventionAttachmentSerializer, \
    InterventionResultNestedSerializer

from partners.models import (
    Intervention,
)


class PDDetailsWrapperRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        data = {'pd-details': data}
        return super(PDDetailsWrapperRenderer, self).render(data, accepted_media_type, renderer_context)


class PRPInterventionListSerializer(serializers.ModelSerializer):

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


class InterventionDetailSerializerV3(serializers.ModelSerializer):
    planned_budget = InterventionBudgetCUSerializer(read_only=True)
    partner = serializers.CharField(source='agreement.partner.name')
    partner_id = serializers.CharField(source='agreement.partner.id', read_only=True)
    prc_review_document_file = serializers.FileField(source='prc_review_document', read_only=True)
    signed_pd_document_file = serializers.FileField(source='signed_pd_document', read_only=True)
    supplies = SupplyPlanNestedSerializer(many=True, read_only=True, required=False)
    distributions = DistributionPlanNestedSerializer(many=True, read_only=True, required=False)
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
            "amendments", "planned_visits", "attachments", "supplies", "distributions", 'permissions', 'partner_id',
        )
