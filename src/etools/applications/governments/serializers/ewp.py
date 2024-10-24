from rest_framework import serializers

from etools.applications.governments import models


class GovernmentEWPSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GovernmentEWP
        fields = '__all__'


class EWPOutputSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = models.EWPOutput
        fields = ['cp_output_id', 'id', 'name', 'workplan_id']

    def get_name(self, obj):
        return f"{obj.cp_output.name}-[{obj.cp_output.wbs}]"


class EWPKeyInterventionSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = models.EWPKeyIntervention
        fields = ['ewp_output_id', 'id', 'name', 'cp_key_intervention_id']

    def get_name(self, obj):
        return f"{obj.cp_key_intervention.name}-[{obj.cp_key_intervention.wbs}]"


class EWPActivitySerializerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EWPActivity
        fields = '__all__'
