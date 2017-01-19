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
from locations.models import Location

from .v1 import PartnerStaffMemberSerializer



from partners.models import (
    Assessment,
    PCA,
    InterventionBudget,
    SupplyPlan,
    DistributionPlan,
    InterventionPlannedVisits,
    Intervention,
    InterventionAmendment,
    PartnerOrganization,
    PartnerType,
    Agreement,
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

    active_staff_members = serializers.SerializerMethodField()
    assessments = serializers.SerializerMethodField()

    class Meta:

        model = PartnerOrganization
        # TODO add missing fields:
        #   Bank Info (just the number of accounts synced from VISION)
        fields = ('vendor_number', 'vision_synced', 'deleted_flag', 'blocked', 'name', 'short_name', 'alternate_id',
                  'alternate_name', 'partner_type', 'cso_type', 'shared_partner', 'address', 'email', 'phone_number',
                  'rating', 'type_of_assessment', 'last_assessment_date', 'total_ct_cp', 'total_ct_cy',
                  'active_staff_members', 'core_values_assessment_date', 'assessments')

    def get_active_staff_members(self, obj):
        return ', '.join([sm.get_full_name() for sm in obj.staff_members.filter(active=True).all()])

    def get_assessments(self, obj):
        return ', '.join(["{} {}".format(a.type, a.completed_date) for a in obj.assessments.all()])


class AssessmentDetailSerializer(serializers.ModelSerializer):
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
        )


class PartnerOrganizationDetailSerializer(serializers.ModelSerializer):

    staff_members = PartnerStaffMemberDetailSerializer(many=True, read_only=True)
    assessments = AssessmentDetailSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerOrganization
        fields = "__all__"


class PartnerOrganizationCreateUpdateSerializer(serializers.ModelSerializer):

    staff_members = PartnerStaffMemberNestedSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerOrganization
        fields = "__all__"


class PartnerStaffMemberPropertiesSerializer(serializers.ModelSerializer):

    partner = PartnerOrganizationSerializer(read_only=True)

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"


class PartnerStaffMemberExportSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"
