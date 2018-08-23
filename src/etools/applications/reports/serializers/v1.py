
from django.db import connection

from rest_framework import serializers

from etools.applications.reports.models import CountryProgramme, Indicator, Result, Section, Unit


class SectionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Section
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


class SectionCreateSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Section
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

    class Meta:
        model = Result
        fields = '__all__'


class ResultLightSerializer(serializers.ModelSerializer):

    class Meta:
        model = Result
        fields = ('id', 'result_name')


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
