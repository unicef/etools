import json
from django.db import transaction
from rest_framework import serializers

from reports.serializers import IndicatorSerializer, OutputSerializer
from locations.models import Location
from partners.serializers.serializers import InterventionSerializer
from partners.models import (
    PartnerOrganization,
    PartnerType,
)


class PartnerOrganizationExportSerializer(serializers.ModelSerializer):

    # pca_set = InterventionSerializer(many=True, read_only=True)
    agreement_count = serializers.SerializerMethodField()
    intervention_count = serializers.SerializerMethodField()
    active_staff_members = serializers.SerializerMethodField()

    class Meta:

        model = PartnerOrganization
        # TODO add missing fields:
        #   Blocked Flag (new property)
        #   Bank Info (just the number of accounts synced from VISION)
        fields = ('vendor_number', 'vision_synced', 'deleted_flag', 'name', 'short_name', 'alternate_id',
                  'alternate_name', 'partner_type', 'cso_type', 'shared_partner', 'address', 'email', 'phone_number',
                  'rating', 'type_of_assessment', 'last_assessment_date', 'total_ct_cp', 'total_ct_cy',
                  'agreement_count', 'intervention_count', 'active_staff_members')

    def get_agreement_count(self, obj):
        return obj.agreement_set.count()

    def get_intervention_count(self, obj):
        if obj.partner_type == PartnerType.GOVERNMENT:
            return obj.work_plans.count()
        return obj.documents.count()

    def get_active_staff_members(self, obj):
        return ', '.join([sm.get_full_name() for sm in obj.staff_members.all()])