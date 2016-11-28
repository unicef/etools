import json
from django.db import transaction
from rest_framework import serializers

from partners.models import PCA
from partners.serializers.serializers import PCASectorSerializer, DistributionPlanSerializer


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
        fields = ('partner_name', 'number', 'partnership_type', 'status', 'title', 'start_date', 'end_date',
                  'result_structure', 'result_structure_name', 'pcasector_set', 'unicef_budget', 'cso_contribution')
