import json
from django.db import transaction
from rest_framework import serializers

from partners.models import PCA
from partners.serializers.v1 import PCASectorSerializer, DistributionPlanSerializer


# Reference Number
# PD/SSFA Type
# Partner Full Name
# Status
# Title
# Start Date
# End Date
#    in the drop-down
# HRP, blank if null
# Sectors
# Total CSO Contribution (USD)
# Total UNICEF Budget (USD)


class InterventionListSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name')
    pcasector_set = PCASectorSerializer(many=True, read_only=True)
    unicef_budget = serializers.IntegerField(source='total_unicef_cash')
    cso_contribution = serializers.IntegerField(source='total_partner_contribution')
    result_structure_name = serializers.CharField(source='result_structure.name')

    class Meta:
        model = PCA
        fields = ('id', 'partner_name', 'number', 'partnership_type', 'status', 'title', 'start_date', 'end_date',
                  'result_structure', 'result_structure_name', 'pcasector_set', 'unicef_budget', 'cso_contribution')

# to be done
# CP Outputs
# RAM Indicators


# FR Number(s)
# Fund Commitment(s)

# how to calculate local currency
# Local Currency of Planned Budget
# Total UNICEF Budget (Local)
# Total CSO Budget (Local)

# Planned Programmatic Visits
# Planned Spot Checks
# Planned Audits

# Supply Plan
# Distribution Plan
# URL

class InterventionExportSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name')
    pcasector_set = PCASectorSerializer(many=True, read_only=True)
    unicef_budget = serializers.IntegerField(source='total_unicef_cash')
    cso_contribution = serializers.IntegerField(source='total_partner_contribution')
    result_structure_name = serializers.CharField(source='result_structure.name')
    agreement_name = serializers.CharField(source='agreement.name')
    locations = serializers.SerializerMethodField()
    unicef_focal_points = serializers.CharField(source='unicef_managers.name')
    cso_authorized_officials = serializers.CharField(source='partner_focal_point.first_name')
    programme_focals = serializers.CharField(source='programme_focal_points.name')

    class Meta:
        model = PCA
        fields = ('status', 'partner_name', 'partnership_type', 'number',  'title', 'start_date', 'end_date',
                  'pcasector_set', 'result_structure_name',  'unicef_budget', 'cso_contribution', 'agreement_name',
                  'office', 'locations', 'unicef_focal_points', 'programme_focal_points', 'population_focus',
                  'initiation_date', 'submission_date', 'review_date', 'partner_manager', 'signed_by_partner_date',
                  'unicef_manager', 'signed_by_unicef_date', 'days_from_submission_to_signed',
                  'days_from_review_to_signed', 'fr_numbers'
                  )

    def get_locations(self, obj):
        return ', '.join([' - '.join(l.location.name, l.location.p_code) for l in obj.locations.all() if l.location])
