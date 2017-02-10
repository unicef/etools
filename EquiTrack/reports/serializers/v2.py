from rest_framework import serializers

from reports.models import Result, AppliedIndicator, IndicatorBlueprint, LowerResult


class ResultListSerializer(serializers.ModelSerializer):

    result_type = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Result
        fields = '__all__'


class AppliedIndicatorSerializer(serializers.ModelSerializer):

    name = serializers.CharField(source='indicator.name')
    unit = serializers.CharField(source='indicator.unit')
    disaggregation_logic = serializers.JSONField()

    class Meta:
        model = AppliedIndicator
        fields = '__all__'




class AppliedIndicatorCUSerializer(serializers.ModelSerializer):

    class Meta:
        model = AppliedIndicator
        fields = '__all__'


    def update(self, instance, validated_data):
        pass


class LowerResultSerializer(serializers.ModelSerializer):

    applied_indicators = AppliedIndicatorSerializer(many=True, read_only=True)
    class Meta:
        model = LowerResult
        fields = '__all__'


class LowerResultCUSerializer(serializers.ModelSerializer):
    class Meta:
        model = LowerResult
        fields = '__all__'