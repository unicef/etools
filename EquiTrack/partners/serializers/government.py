
from partners.models import GovernmentIntervention, GovernmentInterventionResult

from rest_framework import serializers


class GovernmentInterventionResultNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernmentInterventionResult
        fields = ('id', 'intervention', 'result', 'year', 'planned_amount', 'activities', 'unicef_managers', 'sectors',
                  'sections', 'activities_list')

        def validate(self, data):
            """
            Check that the start is before the stop.
            """
            if not data['intervention']:
                raise serializers.ValidationError("There is no partner selected")
            return data

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

        def validate(self, data):
            """
            Check that the start is before the stop.
            """
            if not data['partner']:
                raise serializers.ValidationError("There is no partner selected")
            if not data['country_programme']:
                raise serializers.ValidationError("There is no country programme selected")
            return data


class GovernmentInterventionExportSerializer(serializers.ModelSerializer):

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'