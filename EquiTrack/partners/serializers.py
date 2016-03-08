__author__ = 'jcranwellward'

import json
from django.db import transaction
from rest_framework import serializers

from rest_framework_hstore.fields import HStoreField
from reports.serializers import IndicatorSerializer, OutputSerializer
from locations.models import Location

from .models import (
    GwPCALocation,
    PCA,
    PCASector,
    PartnerStaffMember,
    PartnerOrganization,
    Agreement,
    ResultChain,
    IndicatorReport
)


class PCASectorSerializer(serializers.ModelSerializer):

    sector_name = serializers.CharField(source='sector.name')
    sector_id = serializers.CharField(source='sector.id')

    class Meta:
        model = PCASector


class ResultChainSerializer(serializers.ModelSerializer):
    indicator = IndicatorSerializer()
    disaggregation = HStoreField()
    result = OutputSerializer()

    def create(self, validated_data):
        return validated_data

    class Meta:
        model = ResultChain


class IndicatorReportSerializer(serializers.ModelSerializer):
    disaggregated = serializers.BooleanField(read_only=True)
    partner_staff_member = serializers.SerializerMethodField(read_only=True)
    indicator = serializers.SerializerMethodField(read_only=True)
    disaggregation = serializers.JSONField()

    class Meta:
        model = IndicatorReport

    def get_indicator(self, obj):
        return obj.indicator.id

    def get_partner_staff_member(self, obj):
        return obj.partner_staff_member.id

    def validate(self, data):
        # TODO: handle validation
        return data

    def create(self, validated_data):
        result_chain = validated_data.get('result_chain')
        validated_data['indicator'] = result_chain.indicator

        try:
            with transaction.atomic():
                indicator_report = IndicatorReport.objects.create(**validated_data)
                result_chain.current_progress += validated_data.get('total')
                result_chain.save()
        except:
            raise serializers.ValidationError({'result_chain': "Creation halted for now"})

        return indicator_report

    def update(self, instance, validated_data):
        # TODO: update value on resultchain (atomic)
        raise serializers.ValidationError({'result_chain': "Creation halted for now"})


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
    # pcasector_set = PCASectorSerializer(many=True)
    # results = ResultChainSerializer(many=True)

    def create(self, validated_data):
        # print validated_data
        # intervention, created = PCA.objects.get_or_create(**validated_data)
        # results = validated_data.get('results')
        # validated_data['indicator'] = results.indicator

        try:
            with transaction.atomic():
                intervention = PCA.objects.create(**validated_data)
                # pcasector_set = PCASectorSerializer(many=True)
                # results = ResultChainSerializer(many=True)
                # results.create(validated_data)
                # pcasector_set.create(validated_data)
        except Exception as ex:
            raise serializers.ValidationError({'pcasector': ex.message})

        return intervention

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

    # pca_set = InterventionSerializer(many=True)

    # def __init__(self, *args, **kwargs):
    #     staff_members = kwargs.get('staff_members', None)
    #
    #     super(PartnerOrganizationSerializer, self).__init__(*args, **kwargs)

    # def create(self, validated_data):
    #
    #     staff_members = validated_data.pop('staff_members')
    #     raise serializers.ValidationError({'staff_members': staff_members})
    #
    #     partner = PartnerOrganization.objects.create(**validated_data)
    #
    #     if staff_members:
    #         for mem in staff_members:
    #             PartnerStaffMember.objects.create(partner=partner, **mem)
    #
    #     return partner
    pca_set = InterventionSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerOrganization


class AgreementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Agreement


class PartnerStaffMemberSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerStaffMember


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
