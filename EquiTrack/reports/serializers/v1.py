from __future__ import unicode_literals
from django.db import connection
from rest_framework import serializers

from workplan.serializers import ResultWorkplanPropertySerializer
from workplan.models import ResultWorkplanProperty
from reports.models import (
    ResultType,
    Unit,
    Sector,
    Indicator,
    Result,
    CountryProgramme
)


class SectorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Sector
        fields = ('id', 'name')


class IndicatorSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return '{}{}'.format('[Inactive] ' if not obj.active else '', obj.name)

    class Meta:
        model = Indicator
        fields = ('id', 'name', 'unit', 'total', 'current', 'sector_total', 'sector_current', 'result')


class OutputSerializer(serializers.ModelSerializer):

    class Meta:
        model = Result
        fields = ('id', 'name', 'sector', 'humanitarian_tag')


class SectorCreateSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Sector
        fields = '__all__'


class RAMIndicatorLightSerializer(serializers.ModelSerializer):

    class Meta:
        model = Indicator
        fields = '__all__'


class IndicatorCreateSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Indicator
        fields = ('id', 'name', 'code', 'result')


class ResultSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    workplan_properties = ResultWorkplanPropertySerializer(many=True)

    class Meta:
        model = Result
        fields = '__all__'

    def create(self, validated_data):
        workplan_properties = validated_data.pop("workplan_properties")
        result = Result.objects.create(**validated_data)
        for workplan_property in workplan_properties:
            ResultWorkplanProperty.objects.create(result=result, **workplan_property)
        return result


class ResultLightSerializer(serializers.ModelSerializer):

    class Meta:
        model = Result
        fields = ('id', 'result_name')


class ResultTypeSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = ResultType
        fields = '__all__'


class UnitSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Unit
        fields = '__all__'


class CountryProgrammeSerializer(serializers.ModelSerializer):
    expired = serializers.ReadOnlyField()
    active = serializers.ReadOnlyField()
    special = serializers.SerializerMethodField()
    future = serializers.ReadOnlyField()

    class Meta:
        model = CountryProgramme
        fields = '__all__'

    def get_special(self, cp):
        return False if connection.schema_name in ['palestine'] else cp.special
