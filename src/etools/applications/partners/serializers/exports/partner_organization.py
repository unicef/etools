from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from rest_framework import serializers

from etools.applications.core.mixins import ExportSerializerMixin
from etools.applications.organizations.models import OrganizationType
from etools.applications.partners.models import Assessment, PartnerOrganization
from etools.applications.partners.serializers.fields import HactValuesField


class PartnerStaffMemberExportSerializer(serializers.ModelSerializer):
    active = serializers.SerializerMethodField()
    phone = serializers.CharField(source='profile.phone_number')
    title = serializers.CharField(source='profile.job_title')
    partner_id = serializers.CharField(source="partner.id")

    class Meta:
        model = get_user_model()
        fields = [
            'id', 'email', 'first_name', 'last_name', 'created', 'modified',
            'active', 'phone', 'title', 'partner_id'
        ]

    def get_active(self, obj):
        return "Yes" if obj.is_active else "No"


class PartnerStaffMemberExportFlatSerializer(
        ExportSerializerMixin,
        PartnerStaffMemberExportSerializer
):
    partner_name = serializers.CharField(source="partner.name")

    class Meta(PartnerStaffMemberExportSerializer.Meta):
        fields = PartnerStaffMemberExportSerializer.Meta.fields + ['partner_name']


class PartnerOrganizationExportSerializer(serializers.ModelSerializer):
    staff_members = serializers.SerializerMethodField(label=_("Staff Members"))
    assessments = serializers.SerializerMethodField(
        label=_("Assessment Type (Date Assessed)")
    )
    organization_full_name = serializers.CharField(
        label=_("Organizations Full Name"),
        source='organization.name'
    )
    email_address = serializers.CharField(
        label=_("Email Address"),
        source='email'
    )
    risk_rating = serializers.CharField(label=_("HACT Risk Rating"), source='rating')
    sea_risk_rating_nm = serializers.ReadOnlyField(label=_('SEA Risk Rating'), source='sea_risk_rating_name')
    psea_assessment_date = serializers.DateTimeField(read_only=True, format='%d-%m-%Y')
    highest_risk_rating_type = serializers.ReadOnlyField()
    highest_risk_rating_name = serializers.ReadOnlyField()

    date_last_assessment_against_core_values = serializers.CharField(
        label=_("Date Last Assessed Against Core Values"),
        source='core_values_assessment_date'
    )
    actual_cash_transfer_for_cp = serializers.CharField(
        label=_("Actual Cash Transfer for CP (USD)"),
        source='total_ct_cp'
    )
    actual_cash_transfer_for_current_year = serializers.CharField(
        label=_("Actual Cash Transfer for Current Year (USD)"),
        source='total_ct_ytd'
    )
    marked_for_deletion = serializers.SerializerMethodField(
        label=_("Marked for Deletion")
    )
    blocked = serializers.SerializerMethodField(label=_("Blocked"))
    date_assessed = serializers.CharField(
        label=_("Date Assessed"),
        source='last_assessment_date'
    )
    url = serializers.SerializerMethodField(label=_("URL"))
    shared_with = serializers.SerializerMethodField(label=_("Shared Partner"))
    partner_type = serializers.SerializerMethodField(label=_("Partner Type"))
    planned_visits = serializers.SerializerMethodField(
        label=_("Planned Programmatic Visits")
    )

    class Meta:

        model = PartnerOrganization
        # TODO add missing fields:
        #   Bank Info (just the number of accounts synced from VISION)
        fields = ('vendor_number', 'marked_for_deletion', 'blocked', 'organization_full_name',
                  'short_name', 'alternate_name', 'partner_type', 'shared_with', 'address',
                  'email_address', 'phone_number', 'risk_rating', 'sea_risk_rating_nm', 'psea_assessment_date',
                  'highest_risk_rating_type', 'highest_risk_rating_name', 'type_of_assessment', 'date_assessed',
                  'actual_cash_transfer_for_cp', 'actual_cash_transfer_for_current_year', 'staff_members',
                  'date_last_assessment_against_core_values', 'assessments', 'url', 'basis_for_risk_rating',
                  'planned_visits')

    def get_staff_members(self, obj):
        return ', '.join(['{} ({})'.format(sm.get_full_name(), sm.email)
                          for sm in obj.active_staff_members.all()])

    def get_assessments(self, obj):
        return ', '.join(["{} ({})".format(a.type, a.completed_date) for a in obj.assessments.all()])

    def get_url(self, obj):
        return 'https://{}/pmp/partners/{}/details/'.format(self.context['request'].get_host(), obj.id)

    def get_shared_with(self, obj):
        return ', '.join([x for x in obj.shared_with]) if obj.shared_with else ""

    def get_marked_for_deletion(self, obj):
        return "Yes" if obj.deleted_flag else "No"

    def get_blocked(self, obj):
        return "Yes" if obj.blocked else "No"

    def get_partner_type(self, obj):
        if obj.partner_type == OrganizationType.CIVIL_SOCIETY_ORGANIZATION and obj.cso_type:
            return "{}/{}".format(obj.partner_type, obj.cso_type)
        return "{}".format(obj.partner_type)

    def get_planned_visits(self, obj):
        return ', '.join(['{} (Q1:{} Q2:{}, Q3:{}, Q4:{})'.format(
            pv.year,
            pv.programmatic_q1,
            pv.programmatic_q2,
            pv.programmatic_q3,
            pv.programmatic_q4
        ) for pv in obj.planned_visits.all()])


class PartnerOrganizationExportFlatSerializer(
        ExportSerializerMixin,
        PartnerOrganizationExportSerializer
):
    name = serializers.SerializerMethodField(label=_("Name"))
    vendor_number = serializers.SerializerMethodField(label=_("Vendor Number"))
    short_name = serializers.SerializerMethodField(label=_("Short Name"))
    partner_type = serializers.SerializerMethodField(label=_("Partner Type"))
    cso_type = serializers.SerializerMethodField(label=_("CSO Type"))

    vision_synced = serializers.SerializerMethodField(label=_("VISION Synced"))
    hidden = serializers.SerializerMethodField(label=_("Hidden"))
    hact_values = HactValuesField(label=_("HACT"))

    class Meta:
        model = PartnerOrganization
        exclude = ('sea_risk_rating_name', 'organization')

    def get_name(self, obj):
        return obj.name

    def get_short_name(self, obj):
        return obj.short_name

    def get_vendor_number(self, obj):
        return obj.vendor_number

    def get_partner_type(self, obj):
        return obj.partner_type

    def get_cso_type(self, obj):
        return obj.cso_type

    def get_vision_synced(self, obj):
        return "Yes" if obj.vision_synced else "No"

    def get_hidden(self, obj):
        return "Yes" if obj.hidden else "No"


class AssessmentExportSerializer(serializers.ModelSerializer):
    partner = serializers.CharField(source="partner.name")
    requesting_officer = serializers.CharField(source="requesting_officer.email")
    approving_officer = serializers.CharField(source="approving_officer.email")
    current = serializers.SerializerMethodField()
    report_file = serializers.FileField(source='report', read_only=True)

    class Meta:
        model = Assessment
        fields = "__all__"

    def get_current(self, obj):
        return "Yes" if obj.current else "No"


class AssessmentExportFlatSerializer(ExportSerializerMixin, AssessmentExportSerializer):
    class Meta:
        model = Assessment
        fields = [
            "id",
            "partner",
            "type",
            "names_of_other_agencies",
            "expected_budget",
            "notes",
            "requested_date",
            "requesting_officer",
            "approving_officer",
            "planned_date",
            "completed_date",
            "rating",
            "report_file",
            "current",
        ]
