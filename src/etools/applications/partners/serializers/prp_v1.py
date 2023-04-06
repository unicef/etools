from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection

from rest_framework import serializers
from unicef_attachments.fields import AttachmentSingleFileField

from etools.applications.locations.models import Location
from etools.applications.partners.models import Intervention, InterventionAmendment, PartnerOrganization
from etools.applications.reports.models import (
    AppliedIndicator,
    Disaggregation,
    DisaggregationValue,
    LowerResult,
    ReportingRequirement,
    Result,
    SpecialReportingRequirement,
)
from etools.applications.reports.serializers.v1 import SectionSerializer
from etools.applications.users.models import Realm


class InterventionPDFileSerializer(serializers.ModelSerializer):
    signed_pd_document_file = AttachmentSingleFileField(source='signed_pd_attachment', read_only=True)

    class Meta:
        model = Intervention
        fields = ('signed_pd_document_file',)


class PRPPartnerOrganizationListSerializer(serializers.ModelSerializer):
    rating = serializers.CharField(source='get_rating_display')
    unicef_vendor_number = serializers.CharField(source='vendor_number', read_only=True)

    class Meta:
        model = PartnerOrganization
        fields = (
            "short_name",
            "street_address",
            "last_assessment_date",
            "partner_type",
            "cso_type",
            "total_ct_cp",
            "total_ct_cy",
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
            "core_values_assessment_date",
            "type_of_assessment",
            "sea_risk_rating_name",
            "psea_assessment_date",
            "highest_risk_rating_name",
            "highest_risk_rating_type",
        )


class PRPPartnerStaffMemberSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='full_name', read_only=True)
    phone_num = serializers.CharField(source='profile.phone_number', read_only=True)
    active = serializers.BooleanField(source='is_active')
    title = serializers.CharField(source='profile.job_title')

    class Meta:
        model = get_user_model()
        depth = 1
        fields = ('name', 'title', 'phone_num', 'email', 'active')


class PRPPartnerOrganizationWithStaffMembersSerializer(PRPPartnerOrganizationListSerializer):
    all_staff_members = PRPPartnerStaffMemberSerializer(read_only=True, many=True)

    class Meta(PRPPartnerOrganizationListSerializer.Meta):
        fields = PRPPartnerOrganizationListSerializer.Meta.fields + (
            'all_staff_members',
        )


class UserFocalPointSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = get_user_model()
        depth = 1
        fields = ('name', 'email')


class InterventionAmendmentSerializer(serializers.ModelSerializer):
    amendment_number = serializers.CharField(read_only=True)

    class Meta:
        model = InterventionAmendment
        fields = ('types', 'other_description', 'signed_date', 'amendment_number')


class PRPLocationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Location
        depth = 1
        fields = ('id', 'name', 'p_code', 'admin_level_name', 'admin_level')


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
    title = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()
    display_type = serializers.SerializerMethodField()
    blueprint_id = serializers.PrimaryKeyRelatedField(source='indicator', read_only=True)
    locations = serializers.SerializerMethodField()
    disaggregation = DisaggregationSerializer(read_only=True, many=True)
    target = serializers.JSONField(required=False)
    baseline = serializers.JSONField(required=False)

    def get_title(self, ai):
        return ai.indicator.title if ai.indicator else ''

    def get_unit(self, ai):
        return ai.indicator.unit if ai.indicator else ''

    def get_display_type(self, ai):
        return ai.indicator.display_type if ai.indicator else ''

    def get_locations(self, obj):
        location_qs = obj.locations.values(
            "id",
            "name",
            "p_code",
            "admin_level_name",
            "admin_level",
        )
        for loc in location_qs:
            loc["p_code"] = loc.pop("p_code")
            loc["admin_level_name"] = loc.pop("admin_level_name")
            loc["admin_level"] = loc.pop("admin_level")
        return list(location_qs)

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
            'numerator_label',
            'denominator_label',
            'unit',
            'display_type'
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


class ReportingRequirementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportingRequirement
        fields = ('id', 'start_date', 'end_date', 'due_date', 'report_type')


class SpecialReportingRequirementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialReportingRequirement
        fields = ('id', 'due_date', 'description')


class PRPInterventionListSerializer(serializers.ModelSerializer):

    amendments = InterventionAmendmentSerializer(read_only=True, many=True)
    offices = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    business_area_code = serializers.SerializerMethodField()
    partner_org = PRPPartnerOrganizationListSerializer(read_only=True, source='agreement.partner')
    agreement = serializers.CharField(read_only=True, source='agreement.agreement_number')
    unicef_focal_points = UserFocalPointSerializer(many=True, read_only=True)
    agreement_auth_officers = PRPPartnerStaffMemberSerializer(many=True, read_only=True,
                                                              source='agreement.authorized_officers')
    focal_points = PRPPartnerStaffMemberSerializer(many=True, read_only=True, source='partner_focal_points')
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

    expected_results = serializers.SerializerMethodField()
    update_date = serializers.DateTimeField(source='modified')
    reporting_requirements = serializers.SerializerMethodField()
    special_reports = SpecialReportingRequirementsSerializer(source="special_reporting_requirements",
                                                             many=True, read_only=True)
    sections = SectionSerializer(many=True, read_only=True)
    locations = PRPLocationSerializer(source="flat_locations", many=True, read_only=True)

    disbursement = serializers.DecimalField(source='frs__actual_amt_local__sum', read_only=True,
                                            max_digits=20,
                                            decimal_places=2)

    disbursement_percent = serializers.SerializerMethodField()

    def fr_currencies_ok(self, obj):
        return obj.frs__currency__count == 1 if obj.frs__currency__count else None

    def get_disbursement_percent(self, obj):
        if obj.frs__actual_amt_local__sum is None:
            return None

        if not (self.fr_currencies_ok(obj) and obj.max_fr_currency == obj.planned_budget.currency):
            return "%.1f" % -1.0
        percent = obj.frs__actual_amt_local__sum / obj.total_unicef_cash * 100 \
            if obj.total_unicef_cash and obj.total_unicef_cash > 0 else 0
        return "%.1f" % percent

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

    def get_reporting_requirements(self, obj):
        if obj.status not in [Intervention.ACTIVE, ]:
            return []
        return ReportingRequirementsSerializer(obj.reporting_requirements, many=True).data

    def get_expected_results(self, obj):
        if obj.status not in [Intervention.ACTIVE, ]:
            return []
        return PRPResultSerializer(obj.all_lower_results, many=True).data

    class Meta:
        model = Intervention
        fields = (
            'id',
            'title',
            'document_type',
            'business_area_code',
            'offices',
            'number',
            'status',
            'partner_org',
            'special_reports',
            'sections',
            'agreement',
            'unicef_focal_points',
            'agreement_auth_officers',
            'focal_points',
            'start_date', 'end_date',
            'cso_budget', 'cso_budget_currency',
            'unicef_budget', 'unicef_budget_currency',
            'reporting_requirements',
            'expected_results',
            'update_date',
            'amendments',
            'locations',
            'unicef_budget_cash',
            'unicef_budget_supplies',
            'disbursement',
            'disbursement_percent'
        )


class PRPSyncRealmSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source='country.id')
    organization = serializers.CharField(source='organization.vendor_number')
    group = serializers.CharField(source='group.name')

    class Meta:
        model = Realm
        fields = (
            'country',
            'organization',
            'group',
        )


class PRPSyncUserSerializer(serializers.ModelSerializer):
    realms = PRPSyncRealmSerializer(many=True)

    class Meta:
        model = get_user_model()
        fields = (
            'email',
            'realms',
        )
