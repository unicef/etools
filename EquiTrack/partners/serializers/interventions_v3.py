from __future__ import unicode_literals

from rest_framework import serializers

from funds.serializers import FRsSerializer
from partners.permissions import InterventionPermissions
from partners.serializers.interventions_v2 import InterventionBudgetCUSerializer, SupplyPlanNestedSerializer, \
    DistributionPlanNestedSerializer, InterventionAmendmentCUSerializer, PlannedVisitsNestedSerializer, \
    InterventionLocationSectorNestedSerializer, InterventionAttachmentSerializer, \
    InterventionResultNestedSerializer

from partners.models import (
    Intervention,
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
