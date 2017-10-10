import json

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from reports.models import (
    AppliedIndicator,
    Indicator,
    IndicatorBlueprint,
    LowerResult,
    Result,
)


class OutputListSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="output_name")
    result_type = serializers.SlugRelatedField(slug_field="name", read_only=True)
    expired = serializers.ReadOnlyField()
    special = serializers.ReadOnlyField()

    class Meta:
        model = Result
        fields = '__all__'


class MinimalOutputListSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="output_name")

    class Meta:
        model = Result
        fields = (
            "id",
            "name"
        )


class AppliedIndicatorSerializer(serializers.ModelSerializer):

    name = serializers.CharField(source='indicator.name')
    unit = serializers.CharField(source='indicator.unit')
    disaggregation_logic = serializers.JSONField()

    class Meta:
        model = AppliedIndicator
        fields = '__all__'


class AppliedIndicatorExportSerializer(serializers.ModelSerializer):
    intervention = serializers.CharField(source="lower_result.result_link.intervention.pk")
    lower_result = serializers.CharField(source="lower_result.pk")
    name = serializers.CharField(source="indicator.name")
    unit = serializers.CharField(source="indicator.unit")
    description = serializers.CharField(source="indicator.description")
    code = serializers.CharField(source="indicator.code")
    subdomain = serializers.CharField(source="indicator.subdomain")
    disaggregatable = serializers.SerializerMethodField()
    disaggregation_logic = serializers.SerializerMethodField()

    class Meta:
        model = AppliedIndicator
        fields = (
            "intervention",
            "lower_result",
            "context_code",
            "target",
            "baseline",
            "assumptions",
            "means_of_verification",
            "total",
            "disaggregation_logic",
            "name",
            "unit",
            "description",
            "code",
            "subdomain",
            "disaggregatable",
        )

    def get_disaggregatable(self, obj):
        return "Yes" if obj.indicator.disaggregatable else "No"

    def get_disaggregation_logic(self, obj):
        res = obj.disaggregation_logic
        if isinstance(obj.disaggregation_logic, str):
            res = json.loads(obj.disaggregation_logic)
        return res


class AppliedIndicatorExportFlatSerializer(AppliedIndicatorExportSerializer):
    intervention = serializers.CharField(source="lower_result.result_link.intervention.number")
    lower_result = serializers.CharField(source="lower_result.name")

    class Meta:
        model = AppliedIndicator
        fields = (
            "id",
            "intervention",
            "lower_result",
            "context_code",
            "target",
            "baseline",
            "assumptions",
            "means_of_verification",
            "total",
            "disaggregation_logic",
            "name",
            "unit",
            "description",
            "code",
            "subdomain",
            "disaggregatable",
        )



class IndicatorBlueprintCUSerializer(serializers.ModelSerializer):

    class Meta:
        model = IndicatorBlueprint
        fields = '__all__'


class AppliedIndicatorCUSerializer(serializers.ModelSerializer):

    class Meta:
        model = AppliedIndicator
        fields = '__all__'


class LowerResultSerializer(serializers.ModelSerializer):

    applied_indicators = AppliedIndicatorSerializer(many=True, read_only=True)
    code = serializers.CharField(read_only=True)

    class Meta:
        model = LowerResult
        fields = '__all__'


class LowerResultExportSerializer(serializers.ModelSerializer):
    result_link = serializers.CharField(source="result_link.intervention.pk")

    class Meta:
        model = LowerResult
        fields = "__all__"


class LowerResultExportFlatSerializer(LowerResultExportSerializer):
    result_link = serializers.CharField(source="result_link.intervention.number")


class LowerResultCUSerializer(serializers.ModelSerializer):
    code = serializers.CharField(read_only=True)

    class Meta:
        model = LowerResult
        fields = '__all__'

    def handle_blueprint(self, indicator):

        blueprint_instance, created = IndicatorBlueprint.objects.get_or_create(
            name=indicator.pop('name', None),
            unit=indicator.pop('unit', None),
            # for now all indicator blueprints will be considered dissagregatable
            disaggregatable=True
        )

        return blueprint_instance.pk

    def update_applied_indicators(self, instance, applied_indicators):

        for indicator in applied_indicators:
            indicator['lower_result'] = instance.pk

            indicator['indicator'] = self.handle_blueprint(indicator)

            indicator_id = indicator.get('id')
            if indicator_id:
                try:
                    indicator_instance = AppliedIndicator.objects.get(pk=indicator_id)
                    indicator_serializer = AppliedIndicatorCUSerializer(
                        instance=indicator_instance,
                        data=indicator,
                        partial=True
                    )
                except AppliedIndicator.DoesNotExist:
                    raise ValidationError('Indicator has an ID but could not be found in the db')

            else:
                indicator_serializer = AppliedIndicatorCUSerializer(
                    data=indicator
                )

            if indicator_serializer.is_valid(raise_exception=True):
                indicator_serializer.save()

    @transaction.atomic
    def create(self, validated_data):
        applied_indicators = self.context.pop('applied_indicators', [])
        instance = super(LowerResultCUSerializer, self).create(validated_data)
        self.update_applied_indicators(instance, applied_indicators)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        applied_indicators = self.context.pop('applied_indicators', [])

        self.update_applied_indicators(instance, applied_indicators)

        return super(LowerResultCUSerializer, self).update(instance, validated_data)


class IndicatorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Indicator
        fields = "__all__"


class IndicatorExportSerializer(serializers.ModelSerializer):
    ram_indicator = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
    view_on_dashboard = serializers.SerializerMethodField()

    class Meta:
        model = Indicator
        fields = "__all__"

    def get_ram_indicator(self, obj):
        return "Yes" if obj.ram_indicator else "No"

    def get_active(self, obj):
        return "Yes" if obj.active else "No"

    def get_view_on_dashboard(self, obj):
        return "Yes" if obj.view_on_dashboard else "No"


class IndicatorExportFlatSerializer(IndicatorExportSerializer):
    sector = serializers.CharField(source="sector.name")
    result = serializers.CharField(source="result.name")
    unit = serializers.CharField(source="unit.type")

    class Meta:
        model = Indicator
        fields = "__all__"
