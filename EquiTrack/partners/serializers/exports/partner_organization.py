from __future__ import unicode_literals

from rest_framework import serializers

from partners.models import (
    Assessment,
    PartnerOrganization,
    PartnerStaffMember,
    PartnerType,
)
from partners.serializers.fields import HactValuesField


class PartnerStaffMemberExportSerializer(serializers.ModelSerializer):
    active = serializers.SerializerMethodField()

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"

    def get_active(self, obj):
        return "Yes" if obj.active else "No"


class PartnerStaffMemberExportFlatSerializer(PartnerStaffMemberExportSerializer):
    partner_name = serializers.CharField(source="partner.name")

    class Meta:
        model = PartnerStaffMember
        fields = (
            "id",
            "partner_name",
            "title",
            "first_name",
            "last_name",
            "email",
            "phone",
            "active"
        )


class PartnerOrganizationExportSerializer(serializers.ModelSerializer):
    staff_members = serializers.SerializerMethodField()
    assessments = serializers.SerializerMethodField()
    staff_members = serializers.SerializerMethodField()
    organization_full_name = serializers.CharField(source='name')
    email_address = serializers.CharField(source='email')
    risk_rating = serializers.CharField(source='rating')
    date_last_assessment_against_core_values = serializers.CharField(source='core_values_assessment_date')
    actual_cash_transfer_for_cp = serializers.CharField(source='total_ct_cp')
    actual_cash_transfer_for_current_year = serializers.CharField(source='total_ct_cy')
    marked_for_deletion = serializers.SerializerMethodField()
    blocked = serializers.SerializerMethodField()
    date_assessed = serializers.CharField(source='last_assessment_date')
    url = serializers.SerializerMethodField()
    shared_with = serializers.SerializerMethodField()
    partner_type = serializers.SerializerMethodField()

    class Meta:

        model = PartnerOrganization
        # TODO add missing fields:
        #   Bank Info (just the number of accounts synced from VISION)
        fields = ('vendor_number', 'marked_for_deletion', 'blocked', 'organization_full_name',
                  'short_name', 'alternate_name', 'partner_type', 'shared_with', 'address',
                  'email_address', 'phone_number', 'risk_rating', 'type_of_assessment', 'date_assessed',
                  'actual_cash_transfer_for_cp', 'actual_cash_transfer_for_current_year', 'staff_members',
                  'date_last_assessment_against_core_values', 'assessments', 'url',)

    def get_staff_members(self, obj):
        return ', '.join(['{} ({})'.format(sm.get_full_name(), sm.email)
                          for sm in obj.staff_members.filter(active=True).all()])

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
        if obj.partner_type == PartnerType.CIVIL_SOCIETY_ORGANIZATION and obj.cso_type:
            return "{}/{}".format(obj.partner_type, obj.cso_type)
        return "{}".format(obj.partner_type)


class PartnerOrganizationExportFlatSerializer(PartnerOrganizationExportSerializer):
    vision_synced = serializers.SerializerMethodField()
    hidden = serializers.SerializerMethodField()
    hact_values = HactValuesField()

    class Meta:
        model = PartnerOrganization
        fields = (
            'id',
            'vendor_number',
            'marked_for_deletion',
            'blocked',
            'vision_synced',
            'hidden',
            'organization_full_name',
            'short_name',
            'alternate_name',
            'alternate_id',
            'description',
            'partner_type',
            'shared_with',
            'shared_partner',
            'hact_values',
            'address',
            'street_address',
            'city',
            'postal_code',
            'country',
            'email_address',
            'phone_number',
            'risk_rating',
            'type_of_assessment',
            'date_assessed',
            'actual_cash_transfer_for_cp',
            'actual_cash_transfer_for_current_year',
            'staff_members',
            'date_last_assessment_against_core_values',
            'assessments',
        )

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


class AssessmentExportFlatSerializer(AssessmentExportSerializer):
    class Meta:
        model = Assessment
        fields = (
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
        )
