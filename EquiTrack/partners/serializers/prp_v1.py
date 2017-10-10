from __future__ import unicode_literals
from django.contrib.auth import get_user_model
from django.db import connection

from rest_framework import serializers
from locations.models import Location

from partners.models import (
    Intervention,
    PartnerStaffMember,
    PartnerOrganization
)
from reports.models import Result, AppliedIndicator, LowerResult, Disaggregation


class PartnerSerializer(serializers.ModelSerializer):
    unicef_vendor_number = serializers.CharField(source='vendor_number', read_only=True)

    class Meta:
        model = PartnerOrganization
        depth = 1
        fields = ('name', 'unicef_vendor_number', 'short_name')


class AuthOfficerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)
    phone_num = serializers.CharField(source='phone', read_only=True)

    class Meta:
        model = PartnerStaffMember
        depth = 1
        fields = ('name', 'title', 'phone_num', 'email')


class UserFocalPointSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = get_user_model()
        depth = 1
        fields = ('name', 'email')


class PartnerFocalPointSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = PartnerStaffMember
        depth = 1
        fields = ('name', 'email')


class IndicatorLocationSerializer(serializers.ModelSerializer):
    pcode = serializers.CharField(source='p_code', read_only=True)
    location_type = serializers.CharField(source='gateway.name', read_only=True)

    class Meta:
        model = Location
        depth = 1
        fields = ('name', 'pcode', 'location_type')


class DisaggregationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Disaggregation
        depth = 1
        fields = (
            'id',
            # 'prp_id',
            'name',
            # 'parameter'
        )


class PRPIndicatorSerializer(serializers.ModelSerializer):
    # todo: this class hasn't been tested at all because there are no `AppliedIndicator`s in the current DB
    # todo: need to validate these and fill in missing fields
    title = serializers.CharField(source='indicator.title', read_only=True)
    locations = IndicatorLocationSerializer(read_only=True, many=True)
    disaggregation = DisaggregationSerializer(read_only=True, many=True)

    class Meta:
        model = AppliedIndicator
        fields = (
            'id',
            'title',
            # 'is_cluster',
            'cluster_indicator_id',
            # 'parent_id',
            # 'type',
            # 'pd_frequency',
            # 'display_type',
            'means_of_verification',
            'baseline',
            'target',
            'locations',
            'disaggregation'
        )


class PRPCPOutputResultSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='name', read_only=True)

    class Meta:
        model = Result
        fields = (
            'id',
            'title',
        )


class PRPResultSerializer(serializers.ModelSerializer):
    # todo: figure out where this comes from / if this is right
    title = serializers.CharField(source='name', read_only=True)
    indicators = PRPIndicatorSerializer(many=True, read_only=True, source='applied_indicators')
    cp_output = PRPCPOutputResultSerializer(source='result_link.cp_output', read_only=True)

    class Meta:
        model = LowerResult
        fields = (
            'id',
            'title',
            'result_link',
            'cp_output',
            'indicators',
        )


class PRPInterventionListSerializer(serializers.ModelSerializer):

    # todo: do these need to be lowercased?
    offices = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    business_area_code = serializers.SerializerMethodField()
    partner_org = PartnerSerializer(read_only=True, source='agreement.partner')
    unicef_focal_points = UserFocalPointSerializer(many=True, read_only=True)
    agreement_auth_officers = AuthOfficerSerializer(many=True, read_only=True,
                                                    source='agreement.authorized_officers')
    focal_points = PartnerFocalPointSerializer(many=True, read_only=True, source='partner_focal_points')
    start_date = serializers.DateField(source='start')
    end_date = serializers.DateField(source='end')
    cso_budget = serializers.DecimalField(source='total_partner_contribution', read_only=True,
                                          max_digits=20, decimal_places=2)
    cso_budget_currency = serializers.CharField(source='default_budget_currency', read_only=True)
    unicef_budget = serializers.DecimalField(source='total_unicef_budget', read_only=True,
                                             max_digits=20, decimal_places=2)
    unicef_budget_currency = serializers.CharField(source='default_budget_currency', read_only=True)
    # todo: is this the right field?
    funds_received = serializers.DecimalField(source='total_budget', read_only=True,
                                              max_digits=20, decimal_places=2)
    funds_received_currency = serializers.CharField(source='fr_currency', read_only=True)
    expected_results = PRPResultSerializer(many=True, read_only=True, source='all_lower_results')

    def get_business_area_code(self, obj):
        return connection.tenant.business_area_code

    class Meta:
        model = Intervention
        fields = (
            'id', 'title', 'business_area_code',
            'offices',  # todo: convert to names, not ids
            'number',
            'partner_org',
            'unicef_focal_points',
            'agreement_auth_officers',
            'focal_points',
            'start_date', 'end_date',
            'cso_budget', 'cso_budget_currency',
            'unicef_budget', 'unicef_budget_currency',
            'funds_received', 'funds_received_currency',
            # 'reporting_frequencies',  # todo: figure out where this comes from
            'expected_results',
        )
