import json
from django.db import transaction
from rest_framework import serializers

from reports.serializers import IndicatorSerializer, OutputSerializer
from locations.models import Location
from partners.serializers.serializers import InterventionSerializer
from partners.models import (
    PCA,
    PCASector,
    PartnerOrganization,
    Agreement,
    ResultChain,
    IndicatorReport,
    DistributionPlan,
)


class PartnerOrganizationExportSerializer(serializers.ModelSerializer):

    pca_set = InterventionSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerOrganization
        fields = '__all__'
