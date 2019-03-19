from django.db import connection

from rest_framework import serializers

from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.serializers.partner_organization_v2 import PartnerOrganizationMonitoringListSerializer
from etools.applications.reports.models import CountryProgramme, Indicator, Result, ResultType, Section, Unit


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


class ResultFullSerializer(serializers.ModelSerializer):

    partners = serializers.SerializerMethodField()
    ram_indicators = serializers.SerializerMethodField()
    budget_allocation = serializers.SerializerMethodField()

    @staticmethod
    def get_budget_allocation(obj):
        return 'budget_allocation'

    def get_partners(self, obj):
        result_links = obj.intervention_links.values_list('id', flat=True)
        partners = PartnerOrganization.objects.filter(agreements__interventions__result_links__pk__in=result_links)
        return PartnerOrganizationMonitoringListSerializer(
            partners, many=True, context={'request': self.context['request']}).data

    def get_ram_indicators(self, obj):
        return obj.indicator_set.values('name', 'target')

    class Meta:
        model = Result
        fields = ('name', 'code', 'partners', 'ram_indicators', 'humanitarian_marker_name',
                  'humanitarian_marker_code', 'budget_allocation')
