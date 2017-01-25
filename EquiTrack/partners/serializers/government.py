
from partners.models import GovernmentIntervention

from rest_framework import serializers





class GovernmentInterventionListSerializer(serializers.ModelSerializer):

    class Meta:
        model = GovernmentIntervention
        fields = '__all__'


class GovernmentInterventionDetailSerializer(serializers.ModelSerializer):

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