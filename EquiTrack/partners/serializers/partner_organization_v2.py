from __future__ import unicode_literals
import json

from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth.models import User
from rest_framework import serializers

from partners.serializers.interventions_v2 import InterventionSummaryListSerializer

from partners.models import (
    Assessment,
    Intervention,
    PartnerOrganization,
    PartnerType,
    PartnerStaffMember,
)


class PartnerStaffMemberCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"

    def validate(self, data):
        data = super(PartnerStaffMemberCreateSerializer, self).validate(data)
        email = data.get('email', "")
        active = data.get('active', "")
        existing_user = None

        # user should be active first time it's created
        if not active:
            raise ValidationError({'active': 'New Staff Member needs to be active at the moment of creation'})
        try:
            existing_user = User.objects.filter(Q(username=email) | Q(email=email)).get()
            if existing_user.profile.partner_staff_member:
                raise ValidationError("The email {} for the partner contact is used by another partner contact. "
                                      "Email has to be unique to proceed.".format(email))
        except User.DoesNotExist:
            pass

        return data


class SimpleStaffMemberSerializer(PartnerStaffMemberCreateSerializer):
    """
    A serilizer to be used for nested staff member handling. The 'partner' field
    is removed in this case to avoid validation errors for e.g. when creating
    the partner and the member at the same time.
    """
    class Meta:
        model = PartnerStaffMember
        fields = (
            "id",
            "title",
            "first_name",
            "last_name"
        )


class PartnerStaffMemberNestedSerializer(PartnerStaffMemberCreateSerializer):
    """
    A serilizer to be used for nested staff member handling. The 'partner' field
    is removed in this case to avoid validation errors for e.g. when creating
    the partner and the member at the same time.
    """
    class Meta:
        model = PartnerStaffMember
        fields = (
            "id",
            "title",
            "first_name",
            "last_name",
            "email",
            "phone",
            "active",
        )


class PartnerStaffMemberCreateUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"

    def validate(self, data):
        data = super(PartnerStaffMemberCreateUpdateSerializer, self).validate(data)
        email = data.get('email', "")
        active = data.get('active', "")

        try:
            existing_user = User.objects.get(email=email)
        except User.DoesNotExist:
            # this is a new user
            existing_user = None

        if existing_user and not self.instance and existing_user.profile.partner_staff_member:
            raise ValidationError(
                {'active': 'The email for the partner contact is used by another partner contact. Email has to be '
                           'unique to proceed {}'.format(email)})

        # make sure email addresses are not editable after creation.. user must be removed and re-added
        if self.instance:
            if email != self.instance.email:
                raise ValidationError(
                    "User emails cannot be changed, please remove the user and add another one: {}".format(email))

            # when adding the active tag to a previously untagged user
            # make sure this user has not already been associated with another partnership.
            # TODO: Users should have a json field with country partnerhip pairs not just partnerships
            if active and not self.instance.active and \
                    existing_user and existing_user.profile.partner_staff_member and \
                    existing_user.profile.partner_staff_member != self.instance.pk:
                raise ValidationError(
                    {'active':
                     'The Partner Staff member you are trying to activate is associated with a different partnership'}
                )

        return data


class PartnerStaffMemberDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerStaffMember
        fields = "__all__"


class PartnerStaffMemberExportSerializer(PartnerStaffMemberDetailSerializer):
    active = serializers.SerializerMethodField()

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


class HactValuesField(serializers.Field):
    def to_representation(self, obj):
        return "\n".join(
            ["{}: {}".format(x, obj[x]) for x in sorted(list(obj))]
        )


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


class AssessmentDetailSerializer(serializers.ModelSerializer):

    report_file = serializers.FileField(source='report', read_only=True)

    class Meta:
        model = Assessment
        fields = "__all__"

    def validate(self, data):
        today = timezone.now().date()
        if data["completed_date"] > today:
            raise serializers.ValidationError({'completed_date': ['The Date of Report cannot be in the future']})
        return data


class AssessmentExportSerializer(AssessmentDetailSerializer):
    partner = serializers.CharField(source="partner.name")
    requesting_officer = serializers.CharField(source="requesting_officer.email")
    approving_officer = serializers.CharField(source="approving_officer.email")
    current = serializers.SerializerMethodField()

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


class PartnerOrganizationListSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerOrganization
        fields = (
            "id",
            "vendor_number",
            "deleted_flag",
            "blocked",
            "name",
            "short_name",
            "partner_type",
            "cso_type",
            "rating",
            "shared_partner",
            "shared_with",
            "email",
            "phone_number",
            "total_ct_cp",
            "total_ct_cy",
            "hidden"
        )


class MinimalPartnerOrganizationListSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerOrganization
        fields = (
            "id",
            "name",
        )


class PartnerOrganizationDetailSerializer(serializers.ModelSerializer):

    staff_members = PartnerStaffMemberDetailSerializer(many=True, read_only=True)
    assessments = AssessmentDetailSerializer(many=True, read_only=True)
    hact_values = serializers.SerializerMethodField(read_only=True)
    core_values_assessment_file = serializers.FileField(source='core_values_assessment', read_only=True)
    interventions = serializers.SerializerMethodField(read_only=True)
    hact_min_requirements = serializers.JSONField(read_only=True)
    hidden = serializers.BooleanField(read_only=True)

    def get_hact_values(self, obj):
        return json.loads(obj.hact_values) if isinstance(obj.hact_values, str) else obj.hact_values

    def get_interventions(self, obj):
        interventions = Intervention.objects \
            .filter(agreement__partner=obj) \
            .exclude(status='draft')
        interventions = InterventionSummaryListSerializer(interventions, many=True)
        return interventions.data

    class Meta:
        model = PartnerOrganization
        fields = "__all__"


class PartnerOrganizationCreateUpdateSerializer(serializers.ModelSerializer):

    staff_members = PartnerStaffMemberNestedSerializer(many=True, read_only=True)
    hact_values = serializers.SerializerMethodField(read_only=True)
    core_values_assessment_file = serializers.FileField(source='core_values_assessment', read_only=True)
    hidden = serializers.BooleanField(read_only=True)

    def get_hact_values(self, obj):
        return json.loads(obj.hact_values) if isinstance(obj.hact_values, str) else obj.hact_values

    class Meta:
        model = PartnerOrganization
        fields = "__all__"


class PartnerOrganizationHactSerializer(serializers.ModelSerializer):

    hact_values = serializers.SerializerMethodField(read_only=True)
    hact_min_requirements = serializers.JSONField()

    def get_hact_values(self, obj):
        return json.loads(obj.hact_values) if isinstance(obj.hact_values, str) else obj.hact_values

    class Meta:
        model = PartnerOrganization
        fields = (
            "id",
            "name",
            "short_name",
            "partner_type",
            "cso_type",
            "rating",
            "shared_partner",
            "shared_with",
            "total_ct_cp",
            "total_ct_cy",
            "hact_min_requirements",
            "hact_values",
        )
