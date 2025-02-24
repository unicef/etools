from django.core.exceptions import ObjectDoesNotExist
from django.db import connection

from rest_framework import serializers
from unicef_attachments.fields import AttachmentSingleFileField

from etools.applications.governments.models import GDD, GDDAmendment, GDDKeyIntervention
from etools.applications.partners.serializers.prp_v1 import (
    PRPCPOutputResultSerializer,
    PRPLocationSerializer,
    PRPPartnerOrganizationListSerializer,
    PRPPartnerStaffMemberSerializer,
    ReportingRequirementsSerializer,
    SpecialReportingRequirementsSerializer,
    UserFocalPointSerializer,
)
from etools.applications.reports.serializers.v1 import SectionSerializer


class GDDAmendmentSerializer(serializers.ModelSerializer):
    amendment_number = serializers.CharField(read_only=True)

    class Meta:
        model = GDDAmendment
        fields = ('types', 'other_description', 'signed_date', 'amendment_number')


class PRPKeyInterventionSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='ewp_key_intervention.cp_key_intervention.name', read_only=True)
    cp_output = PRPCPOutputResultSerializer(source='result_link.cp_output.cp_output', read_only=True)

    class Meta:
        model = GDDKeyIntervention
        fields = (
            'id',
            'title',
            'result_link',
            'cp_output',
        )


class PRPGDDListSerializer(serializers.ModelSerializer):
    document_type = serializers.SerializerMethodField()
    amendments = GDDAmendmentSerializer(read_only=True, many=True)
    offices = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    business_area_code = serializers.SerializerMethodField()
    partner_org = PRPPartnerOrganizationListSerializer(read_only=True, source='partner')
    agreement = serializers.SerializerMethodField()
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

    has_signed_document = serializers.SerializerMethodField()

    def get_has_signed_document(self, obj):
        if obj.signed_pd_attachment:
            return True
        return False

    def fr_currencies_ok(self, obj):
        return obj.frs__currency__count == 1 if obj.frs__currency__count else None

    def get_agreement(self, obj):
        return obj.agreement.agreement_number if obj.agreement else '-'

    def get_document_type(self, obj):
        return 'GDD'

    def get_disbursement_percent(self, obj):
        if obj.frs__actual_amt_local__sum is None:
            return None

        if not (self.fr_currencies_ok(obj) and obj.max_fr_currency == obj.planned_budget.currency):
            return "%.1f" % -1.0
        percent = obj.frs__actual_amt_local__sum / obj.total_unicef_cash * 100 \
            if obj.total_unicef_cash and obj.total_unicef_cash > 0 else 0
        return "%.1f" % percent

    def get_unicef_budget_currency(self, obj):
        # GDD.planned_budget isn't a real field, it's a related
        # name from an GDDBudget, and there might not be one.
        try:
            return obj.planned_budget.currency
        except ObjectDoesNotExist:
            return ''
    get_cso_budget_currency = get_unicef_budget_currency

    def get_business_area_code(self, obj):
        return connection.tenant.business_area_code

    def get_reporting_requirements(self, obj):
        if obj.status not in [GDD.ACTIVE, ]:
            return []
        return ReportingRequirementsSerializer(obj.reporting_requirements, many=True).data

    def get_expected_results(self, obj):
        if obj.status not in [GDD.ACTIVE, ]:
            return []
        return PRPKeyInterventionSerializer(obj.all_lower_results, many=True).data

    class Meta:
        model = GDD
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
            'disbursement_percent',
            'has_signed_document'
        )


class GDDFileSerializer(serializers.ModelSerializer):
    signed_pd_document_file = AttachmentSingleFileField(source='signed_pd_attachment', read_only=True)

    class Meta:
        model = GDD
        fields = ('signed_pd_document_file',)
