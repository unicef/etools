import json
from operator import xor

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from reports.serializers.v1 import IndicatorSerializer, OutputSerializer
from partners.serializers.v1 import (
    PartnerOrganizationSerializer,
    PartnerStaffMemberEmbedSerializer,
    InterventionSerializer,
)
from partners.serializers.interventions_v2 import InterventionSummaryListSerializer
from partners.serializers.government import GovernmentInterventionSummaryListSerializer
from locations.models import Location

from .v1 import PartnerStaffMemberSerializer



from partners.models import (
    Assessment,
    Intervention,
    GovernmentIntervention,
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
                raise ValidationError("This user already exists under a different partnership: {}".format(email))
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
                {'active': 'The Partner Staff member you are '
                           'trying to add is associated with a different partnership: {}'.format(email)})

        # make sure email addresses are not editable after creation.. user must be removed and re-added
        if self.instance:
            if email != self.instance.email:
                raise ValidationError("User emails cannot be changed, please remove the user and add another one: {}".format(email))

            # when adding the active tag to a previously untagged user
            # make sure this user has not already been associated with another partnership.
            # TODO: Users should have a json field with country partnerhip pairs not just partnerships
            if active and not self.instance.active and \
                    existing_user and existing_user.profile.partner_staff_member and \
                    existing_user.profile.partner_staff_member != self.instance.pk:
                raise ValidationError(
                    {'active': 'The Partner Staff member you are trying to activate is associated with a different partnership'}
                )

        return data

class PartnerStaffMemberDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerStaffMember
        fields = "__all__"


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
        return ', '.join(["{} ({})".format(sm.get_full_name(), sm.email) for sm in obj.staff_members.filter(active=True).all()])

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
        return "{}/{}".format(obj.partner_type, obj.cso_type)


class AssessmentDetailSerializer(serializers.ModelSerializer):

    report_file = serializers.FileField(source='report', read_only=True)

    class Meta:
        model = Assessment
        fields = "__all__"


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


class PartnerOrganizationDetailSerializer(serializers.ModelSerializer):

    staff_members = PartnerStaffMemberDetailSerializer(many=True, read_only=True)
    assessments = AssessmentDetailSerializer(many=True, read_only=True)
    hact_values = serializers.SerializerMethodField(read_only=True)
    core_values_assessment_file = serializers.FileField(source='core_values_assessment', read_only=True)
    interventions = serializers.SerializerMethodField(read_only=True)

    def get_hact_values(self, obj):
        return json.loads(obj.hact_values) if isinstance(obj.hact_values, str) else obj.hact_values

    def get_interventions(self, obj):
        if obj.partner_type != PartnerType.GOVERNMENT:
            interventions = Intervention.objects \
                .filter(agreement__partner=obj) \
                .exclude(status='draft')

            interventions = InterventionSummaryListSerializer(interventions, many=True)

        else:
            interventions = GovernmentIntervention.objects.filter(partner=obj)

            interventions = GovernmentInterventionSummaryListSerializer(interventions, many=True)

        return interventions.data

    class Meta:
        model = PartnerOrganization
        fields = "__all__"


class PartnerOrganizationCreateUpdateSerializer(serializers.ModelSerializer):

    staff_members = PartnerStaffMemberNestedSerializer(many=True, read_only=True)
    hact_values = serializers.SerializerMethodField(read_only=True)
    core_values_assessment_file = serializers.FileField(source='core_values_assessment', read_only=True)

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


class PartnerStaffMemberPropertiesSerializer(serializers.ModelSerializer):

    partner = PartnerOrganizationSerializer(read_only=True)

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"
