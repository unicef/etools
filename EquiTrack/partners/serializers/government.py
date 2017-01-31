
from partners.models import GovernmentIntervention, GovernmentInterventionResult

from rest_framework import serializers


class GovernmentInterventionResultNestedSerializer(serializers.ModelSerializer):
    model = GovernmentInterventionResult
    fields = '__all__'


class GovernmentInterventionListSerializer(serializers.ModelSerializer):

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'


class GovernmentInterventionDetailSerializer(serializers.ModelSerializer):
    results = GovernmentInterventionResultNestedSerializer(many=True, read_only=True, required=False)

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'

class GovernmentInterventionCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'

class GovernmentInterventionExportSerializer(serializers.ModelSerializer):

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'