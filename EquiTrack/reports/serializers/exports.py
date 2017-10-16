from __future__ import unicode_literals

import json

from rest_framework import serializers

from reports.models import (
    AppliedIndicator,
    Indicator,
    LowerResult,
)


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


class LowerResultExportSerializer(serializers.ModelSerializer):
    result_link = serializers.CharField(source="result_link.intervention.pk")

    class Meta:
        model = LowerResult
        fields = "__all__"


class LowerResultExportFlatSerializer(LowerResultExportSerializer):
    result_link = serializers.CharField(source="result_link.intervention.number")


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
