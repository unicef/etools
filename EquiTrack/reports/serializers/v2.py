from rest_framework import serializers

from workplan.serializers import ResultWorkplanPropertySerializer
from reports.serializers.v1 import MilestoneSerializer
from workplan.models import ResultWorkplanProperty
from reports.models import Result


class ResultSerializer(serializers.ModelSerializer):

    milestones = MilestoneSerializer(many=True, read_only=True)
    workplan_properties = ResultWorkplanPropertySerializer(many=True, read_only=True)

    class Meta:
        model = Result
        fields = '__all__'

    def create(self, validated_data):
        workplan_properties = validated_data.pop("workplan_properties", [])
        result = Result.objects.create(**validated_data)
        for workplan_property in workplan_properties:
            ResultWorkplanProperty.objects.create(result=result, **workplan_property)
        return result
