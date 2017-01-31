
from partners.models import GovernmentIntervention, GovernmentInterventionResult

from rest_framework import serializers


class GovernmentInterventionResultNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernmentInterventionResult
        fields = ('id', 'intervention', 'result', 'year', 'planned_amount', 'activities', 'unicef_managers', 'sectors',
                  'sections', 'activities_list')


class GovernmentInterventionListSerializer(serializers.ModelSerializer):

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'


class GovernmentInterventionDetailSerializer(serializers.ModelSerializer):
    results = GovernmentInterventionResultNestedSerializer(many=True, read_only=True, required=False)

    class Meta:
        model = GovernmentIntervention
        fields = ("id", "number", "created_at", "partner", "result_structure", "country_programme", "results")


class GovernmentInterventionCreateUpdateSerializer(serializers.ModelSerializer):
    results = GovernmentInterventionResultNestedSerializer(many=True, read_only=True, required=False)

    class Meta:
        model = GovernmentIntervention
        fields = ("id", "number", "created_at", "partner", "result_structure", "country_programme", "results")


class GovernmentInterventionExportSerializer(serializers.ModelSerializer):

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'