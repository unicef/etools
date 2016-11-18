__author__ = 'jcranwellward'

import json
from django.db import transaction
from rest_framework import serializers

from reports.serializers import IndicatorSerializer, OutputSerializer
from locations.models import Location

from partners.models import (
    FileType,
    GwPCALocation,
    PCA,
    PCASector,
    PCASectorGoal,
    PCAFile,
    PCAGrant,
    AmendmentLog,
    PartnershipBudget,
    PartnerStaffMember,
    PartnerOrganization,
    Agreement,
    ResultChain,
    IndicatorReport,
    DistributionPlan,
)


class PCASectorGoalSerializer(serializers.ModelSerializer):

    pca_sector = serializers.CharField(read_only=True)

    class Meta:
        model = PCASectorGoal
        fields = (
            'pca_sector',
            'goal'
        )


class PCASectorSerializer(serializers.ModelSerializer):

    sector_name = serializers.CharField(source='sector.name')
    sector_id = serializers.CharField(source='sector.id')
    pcasectorgoal_set = PCASectorGoalSerializer(many=True)

    def create(self, validated_data):

        try:
            pcasectorgoals = validated_data.pop('pcasectorgoal_set')
        except KeyError:
            pcasectorgoals = []

        try:
            instance = PCASector.objects.create(**validated_data)

            for sectorgoal in pcasectorgoals:
                PCASectorGoal.objects.create(pca_sector=instance, **sectorgoal)

        except Exception as ex:
            raise serializers.ValidationError({'instance': ex.message})

        return instance

    class Meta:
        model = PCASector
        fields = '__all__'


class PCAFileSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    attachment = serializers.FileField(read_only=True)

    class Meta:
        model = PCAFile
        fields = (
            "id",
            "attachment",
            "type",
            "pca",
        )


class FileTypeSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = FileType
        fields = '__all__'


class PCAGrantSerializer(serializers.ModelSerializer):

    class Meta:
        model = PCAGrant
        fields = '__all__'


class PartnershipBudgetSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnershipBudget
        fields = '__all__'


class AmendmentLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = AmendmentLog
        fields = '__all__'


class ResultChainSerializer(serializers.ModelSerializer):
    indicator = IndicatorSerializer()
    disaggregation = serializers.JSONField()
    result = OutputSerializer()

    def create(self, validated_data):
        return validated_data

    class Meta:
        model = ResultChain
        fields = '__all__'


class LocationSerializer(serializers.Serializer):

    latitude = serializers.CharField(source='geo_point.y')
    longitude = serializers.CharField(source='geo_point.x')
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
        fields = '__all__'


class IndicatorReportSerializer(serializers.ModelSerializer):
    disaggregated = serializers.BooleanField(read_only=True)
    partner_staff_member = serializers.SerializerMethodField(read_only=True)
    indicator = serializers.SerializerMethodField(read_only=True)
    location_object = LocationSerializer(source='location', read_only=True)
    disaggregation = serializers.JSONField()

    class Meta:
        model = IndicatorReport
        fields = '__all__'

    def get_indicator(self, obj):
        return obj.indicator.id

    def get_partner_staff_member(self, obj):
        return obj.partner_staff_member.id

    def validate(self, data):
        # TODO: handle validation
        # result_chain.partner.partner.id
        user = self.context['request'].user
        rc = data.get('result_chain')
        # make sure only a partner staff member can create a new submission on a partner result chain
        # we could allow superusers by checking for superusers first
        if not (user or rc) or \
                (user.profile.partner_staff_member not in
                    rc.partnership.partner.partnerstaffmember_set.values_list('id', flat=True)):
            raise Exception('hell')

        return data

    def create(self, validated_data):
        result_chain = validated_data.get('result_chain')
        # for multi report this needs to be
        # refreshed from the db in order to reflect the latest value
        result_chain.refresh_from_db()
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
    disaggregation = serializers.JSONField()
    result = OutputSerializer()
    indicator_reports = IndicatorReportSerializer(many=True)

    class Meta:
        model = ResultChain
        fields = '__all__'


class DistributionPlanSerializer(serializers.ModelSerializer):
    item = serializers.CharField(source='item.name')
    site = serializers.CharField(source='site.name')
    quantity = serializers.IntegerField()
    delivered = serializers.IntegerField()

    class Meta:
        model = DistributionPlan
        fields = ('item', 'site', 'quantity', 'delivered')


class InterventionSerializer(serializers.ModelSerializer):

    pca_id = serializers.CharField(source='id', read_only=True)
    pca_title = serializers.CharField(source='title')
    pca_number = serializers.CharField(source='reference_number')
    partner_name = serializers.CharField(source='partner.name')
    partner_id = serializers.CharField(source='partner.id')
    pcasector_set = PCASectorSerializer(many=True, read_only=True)
    results = ResultChainSerializer(many=True, read_only=True)
    distribution_plans = DistributionPlanSerializer(many=True, read_only=True)
    total_budget = serializers.CharField(read_only=True)

    class Meta:
        model = PCA
        fields = '__all__'


class GWLocationSerializer(serializers.ModelSerializer):

    pca_title = serializers.CharField(source='pca.title', read_only=True)
    pca_number = serializers.CharField(source='pca.number', read_only=True)
    pca_id = serializers.CharField(source='pca.id', read_only=True)
    partner_name = serializers.CharField(source='pca.partner.name', read_only=True)
    partner_id = serializers.CharField(source='pca.partner.id', read_only=True)
    sector_name = serializers.CharField(source='pca.sectors', read_only=True)
    sector_id = serializers.CharField(source='pca.sector_id', read_only=True)
    latitude = serializers.CharField(source='location.point.y', read_only=True)
    longitude = serializers.CharField(source='location.point.x', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    location_type = serializers.CharField(source='location.gateway.name', read_only=True)
    gateway_id = serializers.CharField(source='location.gateway.id', read_only=True)

    class Meta:
        model = GwPCALocation
        fields = '__all__'


class PartnerOrganizationSerializer(serializers.ModelSerializer):

    pca_set = InterventionSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerOrganization
        fields = '__all__'


class AgreementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Agreement
        fields = '__all__'


class PartnerStaffMemberSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerStaffMember
        fields = '__all__'


class PartnerStaffMemberPropertiesSerializer(serializers.ModelSerializer):

    partner = PartnerOrganizationSerializer()
    agreement_set = AgreementSerializer(many=True)

    class Meta:
        model = PartnerStaffMember
        fields = '__all__'
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
