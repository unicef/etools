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
    title = serializers.CharField(source="indicator.title")
    unit = serializers.CharField(source="indicator.unit")
    description = serializers.CharField(source="indicator.description")
    code = serializers.CharField(source="indicator.code")
    subdomain = serializers.CharField(source="indicator.subdomain")
    disaggregatable = serializers.SerializerMethodField()
    disaggregation = serializers.SerializerMethodField()

    class Meta:
        model = AppliedIndicator
        fields = "__all__"

    def get_disaggregatable(self, obj):
        return "Yes" if obj.indicator.disaggregatable else "No"

    def get_disaggregation(self, obj):
        res = obj.disaggregation
        if isinstance(obj.disaggregation, str):
            res = json.loads(obj.disaggregation)
        return res


class AppliedIndicatorExportFlatSerializer(AppliedIndicatorExportSerializer):
    intervention = serializers.CharField(source="lower_result.result_link.intervention.number")
    lower_result = serializers.CharField(source="lower_result.name")

    class Meta:
        model = AppliedIndicator
        fields = "__all__"


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


class AppliedIndicatorLocationExportSerializer(serializers.Serializer):
    partner = serializers.CharField(source="indicator.lower_result.result_link.intervention.agreement.partner")
    vendor = serializers.CharField(
        source="indicator.lower_result.result_link.intervention.agreement.partner.vendor_number")
    status = serializers.CharField(source="indicator.lower_result.result_link.intervention.status")
    start = serializers.CharField(source="indicator.lower_result.result_link.intervention.start")
    end = serializers.CharField(source="indicator.lower_result.result_link.intervention.end")
    country_programme = serializers.CharField(
        source="indicator.lower_result.result_link.intervention.agreement.country_programme")
    pd_ref_number = serializers.CharField(source="indicator.lower_result.result_link.intervention.number")
    pd_title = serializers.CharField(source="indicator.lower_result.result_link.intervention.title")
    cp_output = serializers.CharField(source="indicator.lower_result.result_link.cp_output")
    ram_indicators = serializers.SerializerMethodField()
    lower_result = serializers.CharField(source="indicator.lower_result.name")
    indicator = serializers.CharField(source="indicator.indicator.title")
    location = serializers.CharField(source="selected_location.name")
    section = serializers.CharField(source="indicator.section")
    cluster_name = serializers.CharField(source="indicator.cluster_name")
    baseline = serializers.CharField(source="indicator.baseline")
    target = serializers.CharField(source="indicator.target")
    means_of_verification = serializers.CharField(source="indicator.means_of_verification")

    # def get_cp_outputs(self, obj):
    #     return ", ".join([rl.cp_output.name for rl in obj.indicator.lower_result.result_link.all()])

    def get_ram_indicators(self, obj):
        ', '.join([ri.name for ri in obj.indicator.lower_result.result_link.ram_indicators.all()]),
