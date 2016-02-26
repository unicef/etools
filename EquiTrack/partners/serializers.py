__author__ = 'jcranwellward'

import json

from rest_framework import serializers

from rest_framework_hstore.fields import HStoreField
from reports.serializers import IndicatorSerializer, OutputSerializer
from locations.models import Location

from .models import (
    GwPCALocation,
    PCA,
    PCASector,
    IndicatorProgress,
    PartnerStaffMember,
    PartnerOrganization,
    Agreement,
    ResultChain,
    IndicatorReport
)

class IndicatorProgressSerializer(serializers.ModelSerializer):

    indicator = serializers.CharField(source='indicator.name')
    programmed = serializers.IntegerField()
    current = serializers.IntegerField()
    unit = serializers.CharField()

    class Meta:
        model = IndicatorProgress


class PCASectorSerializer(serializers.ModelSerializer):

    sector_name = serializers.CharField(source='sector.name')
    sector_id = serializers.CharField(source='sector.id')
    indicators = serializers.SerializerMethodField()

    def get_indicators(self, pca_sector):
        return IndicatorProgressSerializer(
            pca_sector.indicatorprogress_set.all(),
            many=True
        ).data

    class Meta:
        model = PCASector


class ResultChainSerializer(serializers.ModelSerializer):
    indicator = IndicatorSerializer()
    disaggregation = HStoreField()
    result = OutputSerializer()

    class Meta:
        model = ResultChain


class IndicatorReportSerializer(serializers.ModelSerializer):
    disaggregated = serializers.BooleanField(read_only=True)
    disaggregation = serializers.JSONField()

    class Meta:
        model = IndicatorReport

    def create(self, validated_data):
        # TODO: update value on resultchain (atomic)


        pass

    def update(self, instance, validated_data):
        pass


class ResultChainDetailsSerializer(serializers.ModelSerializer):
    indicator = IndicatorSerializer()
    disaggregation = HStoreField()
    result = OutputSerializer()
    indicator_reports = IndicatorReportSerializer(many=True)

    class Meta:
        model = ResultChain


class InterventionSerializer(serializers.ModelSerializer):

    pca_id = serializers.CharField(source='id')
    pca_title = serializers.CharField(source='title')
    pca_number = serializers.CharField(source='reference_number')
    partner_name = serializers.CharField(source='partner.name')
    partner_id = serializers.CharField(source='partner.id')
    pcasector_set = PCASectorSerializer(many=True)
    results = ResultChainSerializer(many=True)

    class Meta:
        model = PCA


class LocationSerializer(serializers.Serializer):

    latitude = serializers.CharField(source='point.y')
    longitude = serializers.CharField(source='point.x')
    location_name = serializers.CharField(source='name')
    location_type = serializers.CharField(source='gateway.name')
    gateway_id = serializers.CharField(source='gateway.id')
    p_code = serializers.CharField()
    parterships = serializers.SerializerMethodField('get_pcas')

    def get_pcas(self, location):
        pcas = set([
            loc.pca for loc in
            location.gwpcalocation_set.all()
        ])
        return InterventionSerializer(pcas, many=True).data

    class Meta:
        model = Location


class GWLocationSerializer(serializers.ModelSerializer):

    pca_title = serializers.CharField(source='pca.title')
    pca_number = serializers.CharField(source='pca.number')
    pca_id = serializers.CharField(source='pca.id')
    partner_name = serializers.CharField(source='pca.partner.name')
    partner_id = serializers.CharField(source='pca.partner.id')
    sector_name = serializers.CharField(source='pca.sectors')
    sector_id = serializers.CharField(source='pca.sector_id')
    latitude = serializers.CharField(source='location.point.y')
    longitude = serializers.CharField(source='location.point.x')
    location_name = serializers.CharField(source='location.name')
    location_type = serializers.CharField(source='location.gateway.name')
    gateway_id = serializers.CharField(source='location.gateway.id')

    class Meta:
        model = GwPCALocation


class PartnerOrganizationSerializer(serializers.ModelSerializer):

    pca_set = InterventionSerializer(many=True)

    class Meta:
        model = PartnerOrganization


class AgreementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Agreement



class PartnerStaffMemberPropertiesSerializer(serializers.ModelSerializer):

    partner = PartnerOrganizationSerializer()
    agreement_set = AgreementSerializer(many=True)

    class Meta:
        model = PartnerStaffMember
        # fields = (
        # )


class RapidProRequest(serializers.Serializer):

    relayer	= serializers.CharField()
    phone = serializers.CharField(required=True)
    text = serializers.CharField(required=True)
    flow = serializers.CharField()
    step = serializers.CharField()
    time = serializers.DateTimeField()
    values = serializers.CharField()

    def restore_fields(self, data, files):

        restored_data = super(RapidProRequest, self).restore_fields(data, files)
        if restored_data['values']:
            restored_data['values'] = json.loads(restored_data['values'])
        return restored_data
