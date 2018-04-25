
import json

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils import six, timezone
from rest_framework import serializers

from attachments.serializers_fields import AttachmentSingleFileField
from EquiTrack.serializers import SnapshotModelSerializer
from partners.serializers.interventions_v2 import InterventionListSerializer

from partners.models import (
    Assessment,
    Intervention,
    PartnerOrganization,
    PartnerStaffMember,
    PlannedEngagement
)


class PartnerStaffMemberCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"

    def validate(self, data):
        data = super(PartnerStaffMemberCreateSerializer, self).validate(data)
        email = data.get('email', "")
        active = data.get('active', "")
        User = get_user_model()
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
    A serializer to be used for nested staff member handling. The 'partner' field
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
    A serializer to be used for nested staff member handling. The 'partner' field
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
        User = get_user_model()

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


class AssessmentDetailSerializer(serializers.ModelSerializer):
    report_attachment = AttachmentSingleFileField(read_only=True)
    report_file = serializers.FileField(source='report', read_only=True)
    report = serializers.FileField(required=True)
    completed_date = serializers.DateField(required=True)

    class Meta:
        model = Assessment
        fields = "__all__"

    def validate_completed_date(self, completed_date):
        today = timezone.now().date()
        if completed_date > today:
            raise serializers.ValidationError('The Date of Report cannot be in the future')
        return completed_date


class PartnerOrganizationListSerializer(serializers.ModelSerializer):
    rating = serializers.CharField(source='get_rating_display')

    class Meta:
        model = PartnerOrganization
        fields = (
            "street_address",
            "last_assessment_date",
            "address",
            "city",
            "postal_code",
            "country",
            "id",
            "vendor_number",
            "deleted_flag",
            "blocked",
            "name",
            "short_name",
            "partner_type",
            "cso_type",
            "rating",
            "shared_with",
            "email",
            "phone_number",
            "total_ct_cp",
            "total_ct_cy",
            "net_ct_cy",
            "reported_cy",
            "total_ct_ytd",
            "hidden",
            "basis_for_risk_rating",
        )


class MinimalPartnerOrganizationListSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerOrganization
        fields = (
            "id",
            "name",
        )


class PlannedEngagementSerializer(serializers.ModelSerializer):

    spot_check_mr = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_spot_check_mr(obj):
        spot_check_mr = {
            'q1': 0,
            'q2': 0,
            'q3': 0,
            'q4': 0,
        }
        if obj.spot_check_mr in spot_check_mr:
            spot_check_mr[obj.spot_check_mr] += 1
        return spot_check_mr

    class Meta:
        model = PlannedEngagement
        fields = (
            "id",
            "spot_check_mr",
            "spot_check_follow_up_q1",
            "spot_check_follow_up_q2",
            "spot_check_follow_up_q3",
            "spot_check_follow_up_q4",
            "scheduled_audit",
            "special_audit",
            "total_spot_check_follow_up_required",
            "spot_check_required",
            "required_audit"
        )


class PlannedEngagementNestedSerializer(serializers.ModelSerializer):
    """
    A serializer to be used for nested planned engagement handling. The 'partner' field
    is removed in this case to avoid validation errors for e.g. when creating
    the partner and the engagement at the same time.
    """
    spot_check_mr = serializers.JSONField()

    def validate(self, data):
        data = super(PlannedEngagementNestedSerializer, self).validate(data)
        spot_check_mr = data.get('spot_check_mr', 0)
        partner = data.get('partner', None)

        spot_check_mr_number = 1 if spot_check_mr else 0
        if spot_check_mr_number > partner.min_req_spot_checks:
            raise ValidationError("Based on Liquidation, you cannot set this value")
        return data

    def validate_spot_check_mr(self, attrs):
        quarters = []
        for key, value in attrs.items():
            try:
                value = int(value)
            except ValueError:
                raise ValidationError("You can select only MR in one quarter")
            else:
                if value:
                    if value != 1:
                        raise ValidationError("If selected, the value has to be 1")
                    quarters.append(key)
        if len(quarters) > 1:
            raise ValidationError("You can select only MR in one quarter")
        elif len(quarters) == 1:
            return quarters[0]
        else:
            return 0

    class Meta:
        model = PlannedEngagement
        fields = '__all__'


class PartnerOrganizationDetailSerializer(serializers.ModelSerializer):

    staff_members = PartnerStaffMemberDetailSerializer(many=True, read_only=True)
    assessments = AssessmentDetailSerializer(many=True, read_only=True)
    planned_engagement = PlannedEngagementSerializer(read_only=True)
    hact_values = serializers.SerializerMethodField(read_only=True)
    core_values_assessment_file = serializers.FileField(source='core_values_assessment', read_only=True)
    core_values_assessment_attachment = AttachmentSingleFileField(read_only=True)
    interventions = serializers.SerializerMethodField(read_only=True)
    hact_min_requirements = serializers.JSONField(read_only=True)
    hidden = serializers.BooleanField(read_only=True)

    def get_hact_values(self, obj):
        return json.loads(obj.hact_values) if isinstance(obj.hact_values, six.text_type) else obj.hact_values

    def get_interventions(self, obj):
        interventions = InterventionListSerializer(self.get_related_interventions(obj), many=True)
        return interventions.data

    def get_related_interventions(self, partner):
        qs = Intervention.objects.frs_qs()\
            .filter(agreement__partner=partner)\
            .exclude(status='draft')
        return qs

    class Meta:
        model = PartnerOrganization
        fields = "__all__"


class PartnerOrganizationCreateUpdateSerializer(SnapshotModelSerializer):

    staff_members = PartnerStaffMemberNestedSerializer(many=True, read_only=True)
    planned_engagement = PlannedEngagementNestedSerializer(read_only=True)
    hact_values = serializers.SerializerMethodField(read_only=True)
    core_values_assessment_file = serializers.FileField(source='core_values_assessment', read_only=True)
    hidden = serializers.BooleanField(read_only=True)

    def get_hact_values(self, obj):
        return json.loads(obj.hact_values) if isinstance(obj.hact_values, six.text_type) else obj.hact_values

    def validate(self, data):
        data = super(PartnerOrganizationCreateUpdateSerializer, self).validate(data)

        type_of_assessment = data.get('type_of_assessment', self.instance.type_of_assessment)
        rating = data.get('rating', self.instance.rating)
        basis_for_risk_rating = data.get('basis_for_risk_rating', self.instance.basis_for_risk_rating)

        if basis_for_risk_rating and \
                type_of_assessment in [PartnerOrganization.HIGH_RISK_ASSUMED, PartnerOrganization.LOW_RISK_ASSUMED]:
            raise ValidationError(
                {'basis_for_risk_rating': 'The basis for risk rating has to be blank if Type is Low or High'})

        if basis_for_risk_rating and \
                rating == PartnerOrganization.RATING_NON_ASSESSED and \
                type_of_assessment == PartnerOrganization.MICRO_ASSESSMENT:
            raise ValidationError({
                'basis_for_risk_rating':
                    'The basis for risk rating has to be blank if rating is Not Required and type is Micro Assessment'
            })

        return data

    class Meta:
        model = PartnerOrganization
        fields = "__all__"
        extra_kwargs = {
            "partner_type": {
                "error_messages": {
                    "null": u'Vendor record must belong to PRG2 account group (start from 2500 series)'
                }
            }
        }


class PartnerOrganizationHactSerializer(serializers.ModelSerializer):

    planned_engagement = PlannedEngagementSerializer(read_only=True)
    hact_values = serializers.SerializerMethodField(read_only=True)
    hact_min_requirements = serializers.JSONField()
    rating = serializers.CharField(source='get_rating_display')

    def get_hact_values(self, obj):
        return json.loads(obj.hact_values) if isinstance(obj.hact_values, six.text_type) else obj.hact_values

    class Meta:
        model = PartnerOrganization
        fields = (
            "id",
            "name",
            "vendor_number",
            "short_name",
            "type_of_assessment",
            "partner_type",
            "partner_type_slug",
            "cso_type",
            "rating",
            "shared_with",
            "total_ct_cp",
            "total_ct_cy",
            "net_ct_cy",
            "reported_cy",
            "total_ct_ytd",
            "hact_values",
            "hact_min_requirements",
            "flags",
            "planned_engagement"
        )
