from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection

from rest_framework import serializers

from etools.applications.locations.models import Location
from etools.applications.partners.models import (Intervention, InterventionAmendment, InterventionReportingPeriod,
                                                 PartnerOrganization, PartnerStaffMember,)
from etools.applications.reports.models import (AppliedIndicator, Disaggregation, DisaggregationValue,
                                                LowerResult, ReportingRequirement, Result,)
from etools.applications.reports.serializers.v1 import SectorSerializer


class PRPPartnerOrganizationListSerializer(serializers.ModelSerializer):
    rating = serializers.CharField(source='get_rating_display')
    unicef_vendor_number = serializers.CharField(source='vendor_number', read_only=True)

    class Meta:
        model = PartnerOrganization
        fields = (
            "short_name",
            "street_address",
            "last_assessment_date",
            "address",
            "city",
            "postal_code",
            "country",
            "id",
            "unicef_vendor_number",
            "name",
            "alternate_name",
            "rating",
            "email",
            "phone_number",
            "basis_for_risk_rating",
            "core_values_assessment_date"
        )


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


class InterventionAmendmentSerializer(serializers.ModelSerializer):
    amendment_number = serializers.CharField(read_only=True)

    class Meta:
        model = InterventionAmendment
        fields = ('types', 'other_description', 'signed_date', 'amendment_number')


class PRPLocationSerializer(serializers.ModelSerializer):
    pcode = serializers.CharField(source='p_code', read_only=True)
    location_type = serializers.CharField(source='gateway.name', read_only=True)
    admin_level = serializers.IntegerField(source='gateway.admin_level')

    class Meta:
        model = Location
        depth = 1
        fields = ('id', 'name', 'pcode', 'location_type', 'admin_level')


class DisaggregationValueSerilizer(serializers.ModelSerializer):

    class Meta:
        model = DisaggregationValue
        fields = (
            'value',
            'active',
            'id'
        )


class DisaggregationSerializer(serializers.ModelSerializer):
    disaggregation_values = DisaggregationValueSerilizer(read_only=True, many=True)

    class Meta:
        model = Disaggregation
        fields = (
            'id',
            # 'prp_id',
            'name',
            'disaggregation_values'
        )


class PRPIndicatorSerializer(serializers.ModelSerializer):
    # todo: this class hasn't been tested at all because there are no `AppliedIndicator`s in the current DB
    # todo: need to validate these and fill in missing fields
    title = serializers.CharField(source='indicator.title', read_only=True)
    blueprint_id = serializers.IntegerField(source='indicator.id', read_only=True)
    locations = PRPLocationSerializer(read_only=True, many=True)
    disaggregation = DisaggregationSerializer(read_only=True, many=True)

    class Meta:
        model = AppliedIndicator
        fields = (
            'id',
            'title',
            'blueprint_id',
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
            'disaggregation',
            'is_high_frequency',
            'is_active',
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


class ReportingPeriodsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionReportingPeriod
        fields = ('id', 'start_date', 'end_date', 'due_date')


class ReportingRequirementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportingRequirement
        fields = ('id', 'start_date', 'end_date', 'due_date', 'report_type', 'description')


class PRPInterventionListSerializer(serializers.ModelSerializer):

    # todo: do these need to be lowercased?
    amendments = InterventionAmendmentSerializer(read_only=True, many=True)
    offices = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    business_area_code = serializers.SerializerMethodField()
    partner_org = PRPPartnerOrganizationListSerializer(read_only=True, source='agreement.partner')
    agreement = serializers.CharField(read_only=True, source='agreement.agreement_number')
    unicef_focal_points = UserFocalPointSerializer(many=True, read_only=True)
    agreement_auth_officers = AuthOfficerSerializer(many=True, read_only=True,
                                                    source='agreement.authorized_officers')
    focal_points = PartnerFocalPointSerializer(many=True, read_only=True, source='partner_focal_points')
    start_date = serializers.DateField(source='start')
    end_date = serializers.DateField(source='end')
    cso_budget = serializers.DecimalField(source='total_partner_contribution', read_only=True,
                                          max_digits=20, decimal_places=2)
    cso_budget_currency = serializers.SerializerMethodField(read_only=True)
    unicef_budget = serializers.DecimalField(source='total_unicef_budget', read_only=True,
                                             max_digits=20, decimal_places=2)
    unicef_budget_supplies = serializers.DecimalField(source='total_in_kind_amount', read_only=True,
                                                      max_digits=20, decimal_places=2)
    unicef_budget_cash = serializers.DecimalField(source='total_unicef_cash', read_only=True,
                                                  max_digits=20, decimal_places=2)
    unicef_budget_currency = serializers.SerializerMethodField(read_only=True)
    # TODO: update this after FR Validation changes, pending new Insight API changes.

    expected_results = PRPResultSerializer(many=True, read_only=True, source='all_lower_results')
    update_date = serializers.DateTimeField(source='modified')
    reporting_periods = ReportingPeriodsSerializer(many=True, read_only=True)
    reporting_requirements = ReportingRequirementsSerializer(many=True, read_only=True)
    sections = SectorSerializer(source="combined_sections", many=True, read_only=True)
    locations = PRPLocationSerializer(source="flat_locations", many=True, read_only=True)

    def get_unicef_budget_currency(self, obj):
        # Intervention.planned_budget isn't a real field, it's a related
        # name from an InterventionBudget, and there might not be one.
        try:
            return obj.planned_budget.currency
        except ObjectDoesNotExist:
            return ''
    get_cso_budget_currency = get_unicef_budget_currency

    def get_business_area_code(self, obj):
        return connection.tenant.business_area_code

    def get_funds_received(self, obj):
        return obj.total_frs['total_actual_amt']

    class Meta:
        model = Intervention
        fields = (
            'id', 'title', 'business_area_code',
            'offices',  # todo: convert to names, not ids
            'number',
            'status',
            'partner_org',
            'sections',
            'agreement',
            'unicef_focal_points',
            'agreement_auth_officers',
            'focal_points',
            'start_date', 'end_date',
            'cso_budget', 'cso_budget_currency',
            'unicef_budget', 'unicef_budget_currency',
            'reporting_periods',
            'reporting_requirements',
            'expected_results',
            'update_date',
            'amendments',
            'locations',
            'unicef_budget_cash',
            'unicef_budget_supplies'
        )
