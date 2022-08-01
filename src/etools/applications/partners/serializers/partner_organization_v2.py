import datetime
import itertools

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Q
from django.utils import timezone

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.serializers import AttachmentSerializerMixin
from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.field_monitoring.planning.models import MonitoringActivity, MonitoringActivityGroup
from etools.applications.partners.models import (
    Agreement,
    Assessment,
    CoreValuesAssessment,
    Intervention,
    OrganizationType,
    PartnerOrganization,
    PartnerPlannedVisits,
    PartnerStaffMember,
    PlannedEngagement,
)
from etools.applications.partners.serializers.interventions_v2 import (
    InterventionListSerializer,
    InterventionMonitorSerializer,
)
from etools.applications.users.serializers import MinimalUserSerializer


class CoreValuesAssessmentSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    attachment = AttachmentSingleFileField()
    # assessment = serializers.FileField(required=True)
    assessment_file = serializers.FileField(source='assessment', read_only=True)

    class Meta:
        model = CoreValuesAssessment
        fields = "__all__"


class PartnerStaffMemberCreateSerializer(serializers.ModelSerializer):
    # legacy serializer; not actually being used for creating

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"

    def validate(self, data):
        data = super().validate(data)
        email = data.get('email', "")
        active = data.get('active', "")
        User = get_user_model()
        existing_user = None

        # user should be active first time it's created
        if not active:
            raise ValidationError({'active': 'New Staff Member needs to be active at the moment of creation'})
        try:
            existing_user = User.objects.filter(Q(username=email) | Q(email=email)).get()
        except User.DoesNotExist:
            pass
        else:
            if bool(existing_user.staff_member_country()):
                raise ValidationError(
                    "The email {} for the partner contact is used by another "
                    "partner contact. Email has to be unique to "
                    "proceed.".format(email)
                )

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
        read_only_fields = ['user', ]

    def validate(self, data):
        data = super().validate(data)
        email = data.get('email', "")
        active = data.get('active')
        User = get_user_model()

        if not self.instance:
            if email != email.lower():
                raise ValidationError(
                    {"email": "Email cannot have uppercase characters."},
                )

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                pass

            else:
                if user.is_unicef_user():
                    raise ValidationError('Unable to associate staff member to UNICEF user')

                if bool(user.get_staff_member_country()):
                    raise ValidationError(
                        {
                            'active': 'The email for the partner contact is used by another partner contact. '
                                      'Email has to be unique to proceed {}'.format(email)
                        }
                    )

                data['user'] = user
        else:
            # make sure email addresses are not editable after creation.. user must be removed and re-added
            if email != self.instance.email:
                raise ValidationError(
                    {
                        "email": "User emails cannot be changed, please remove"
                        " the user and add another one: {}".format(email)
                    }
                )

            # when adding the active tag to a previously untagged user
            if active and not self.instance.active:
                # make sure this user has not already been associated with another partnership.
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    pass
                else:
                    psm_country = user.get_staff_member_country()
                    if psm_country and psm_country != connection.tenant:
                        raise ValidationError({
                            'active': 'The Partner Staff member you are trying to activate is associated '
                                      'with a different Partner Organization'
                        })

            # disabled is unavailable if user already synced to PRP to avoid data inconsistencies
            if self.instance.active and not active:
                if Intervention.objects.filter(
                    Q(date_sent_to_partner__isnull=False, agreement__partner__staff_members=self.instance) |
                    Q(
                        ~Q(status=Intervention.DRAFT),
                        Q(partner_focal_points=self.instance) | Q(partner_authorized_officer_signatory=self.instance),
                    ),
                ).exists():
                    raise ValidationError({'active': 'User already synced to PRP and cannot be disabled. '
                                                     'Please instruct the partner to disable from PRP'})

        return data

    def create(self, validated_data):
        User = get_user_model()
        if 'user' not in validated_data:
            validated_data['user'] = User.objects.create(
                first_name=validated_data.get('first_name'),
                last_name=validated_data.get('last_name'),
                username=validated_data['email'],
                email=validated_data['email'],
                is_staff=False,
                is_active=True,
            )

        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        # if inactive, remove from DRAFT Agreements and PDs
        if not instance.active:
            agreement_qs = instance.agreement_authorizations.filter(
                status=Agreement.DRAFT,
            )
            for agreement in agreement_qs.all():
                agreement.authorized_officers.remove(instance)
            pd_qs = Intervention.objects.filter(
                status=Intervention.DRAFT,
                partner_focal_points=instance,
            )
            for pd in pd_qs.all():
                pd.partner_focal_points.remove(instance)

        return instance


class PartnerStaffMemberDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerStaffMember
        fields = "__all__"


class PartnerStaffMemberUserSerializer(serializers.ModelSerializer):
    user = MinimalUserSerializer()

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"


class AssessmentDetailSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    report_attachment = AttachmentSingleFileField()
    report_file = serializers.FileField(source='report', read_only=True)
    report = serializers.FileField(required=False)
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
    name = serializers.CharField(source='organization.name')
    vendor_number = serializers.CharField(source='organization.vendor_number')
    short_name = serializers.CharField(source='organization.short_name')
    partner_type = serializers.CharField(source='organization.organization_type')
    cso_type = serializers.CharField(source='organization.cso_type')

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
            "psea_assessment_date",
            "sea_risk_rating_name",
        )


class PartnerOrgPSEADetailsSerializer(serializers.ModelSerializer):
    staff_members = serializers.SerializerMethodField()
    name = serializers.CharField(source='organization.name')
    vendor_number = serializers.CharField(source='organization.vendor_number')
    short_name = serializers.CharField(source='organization.short_name')
    partner_type = serializers.CharField(source='organization.organization_type')
    cso_type = serializers.CharField(source='organization.cso_type')

    def get_staff_members(self, obj):
        return [s.get_full_name() for s in obj.staff_members.all()]

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
            "name",
            "short_name",
            "partner_type",
            "cso_type",
            "staff_members"
        )


class MinimalPartnerOrganizationListSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerOrganization
        fields = (
            "id",
            "name",
        )


class PartnerOrganizationMonitoringListSerializer(serializers.ModelSerializer):
    prog_visit_mr = serializers.CharField(source='min_req_programme_visits')
    interventions = serializers.SerializerMethodField(read_only=True)

    def get_interventions(self, obj):
        related_interventions = Intervention.objects.filter(agreement__partner=obj).exclude(status='draft')
        return InterventionMonitorSerializer(related_interventions, many=True).data

    class Meta:
        model = PartnerOrganization
        fields = (
            "id",
            "name",
            "prog_visit_mr",
            "interventions",
        )


class PlannedEngagementSerializer(serializers.ModelSerializer):

    class Meta:
        model = PlannedEngagement
        fields = (
            "id",
            "spot_check_follow_up",
            "spot_check_planned_q1",
            "spot_check_planned_q2",
            "spot_check_planned_q3",
            "spot_check_planned_q4",
            "spot_check_required",
            "scheduled_audit",
            "special_audit",
            "total_spot_check_planned",
            "required_audit"
        )


class PlannedEngagementNestedSerializer(serializers.ModelSerializer):
    """
    A serializer to be used for nested planned engagement handling. The 'partner' field
    is removed in this case to avoid validation errors for e.g. when creating
    the partner and the engagement at the same time.
    """

    class Meta:
        model = PlannedEngagement
        fields = '__all__'


class PartnerPlannedVisitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerPlannedVisits
        fields = "__all__"

    def is_valid(self, **kwargs):
        """If no year provided, default to current year

        Do not expect id to be provided, so check if object exists already
        for partner and year provided and if so,
        set instance to this object
        """
        if not self.initial_data.get("year"):
            self.initial_data["year"] = datetime.date.today().year
        try:
            self.instance = self.Meta.model.objects.get(
                partner=self.initial_data.get("partner"),
                year=self.initial_data.get("year"),
            )
            if self.instance.partner.partner_type != OrganizationType.GOVERNMENT:
                raise ValidationError({'partner': 'Planned Visit can be set only for Government partners'})

        except self.Meta.model.DoesNotExist:
            self.instance = None

        return super().is_valid(**kwargs)


class MonitoringActivityGroupSerializer(serializers.Field):
    default_error_messages = {
        'bad_value': 'List was expected, {type} provided',
    }

    def to_internal_value(self, data):
        if not data:
            return data

        if not isinstance(data, list):
            self.fail('bad_value', type=type(data))

        if not hasattr(self.root, 'instance'):
            return []

        partner = self.root.instance
        hact_activities = MonitoringActivity.objects.filter_hact_for_partner(partner.id)
        activities = {
            activity.id: activity
            for activity in hact_activities.filter(id__in=itertools.chain(*data))
        }

        result = []
        for group in data:
            result.append([activities[activity] for activity in group if activity in activities])
        result = list(filter(lambda x: x, result))

        return result

    def to_representation(self, data):
        group_objects = list(
            self.parent.instance.monitoring_activity_groups.values_list('id', 'monitoring_activities__id')
        )
        groups = {group_id: [] for group_id in sorted(set(group[0] for group in group_objects))}
        for group in group_objects:
            groups[group[0]].append(group[1])

        return list(groups.values())


class PartnerOrganizationDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='organization.name', read_only=True)
    vendor_number = serializers.CharField(source='organization.vendor_number', read_only=True)
    short_name = serializers.CharField(source='organization.short_name', read_only=True)
    partner_type = serializers.CharField(source='organization.organization_type', read_only=True)
    cso_type = serializers.CharField(source='organization.cso_type', read_only=True)
    staff_members = PartnerStaffMemberDetailSerializer(many=True, read_only=True)
    assessments = AssessmentDetailSerializer(many=True, read_only=True)
    planned_engagement = PlannedEngagementSerializer(read_only=True)
    interventions = serializers.SerializerMethodField(read_only=True)
    hact_min_requirements = serializers.JSONField(read_only=True)
    hidden = serializers.BooleanField(read_only=True)
    planned_visits = PartnerPlannedVisitsSerializer(many=True, read_only=True, required=False)
    core_values_assessments = CoreValuesAssessmentSerializer(many=True, read_only=True, required=False)
    partner_type_slug = serializers.ReadOnlyField()
    flags = serializers.ReadOnlyField()
    sea_risk_rating_name = serializers.CharField(label="psea_risk_rating")
    highest_risk_rating_type = serializers.CharField(label="highest_risk_type")
    highest_risk_rating_name = serializers.CharField(label="highest_risk_rating")
    monitoring_activity_groups = MonitoringActivityGroupSerializer()

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
        exclude = ('organization',)


class PartnerOrganizationDashboardSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='organization.name')
    vendor_number = serializers.CharField(source='organization.vendor_number')
    partner_type = serializers.CharField(source='organization.organization_type')
    sections = serializers.ReadOnlyField(read_only=True)
    locations = serializers.ReadOnlyField(read_only=True)
    action_points = serializers.ReadOnlyField(read_only=True)
    total_ct_cp = serializers.FloatField(read_only=True)
    total_ct_ytd = serializers.FloatField(read_only=True)
    outstanding_dct_amount_6_to_9_months_usd = serializers.FloatField(read_only=True)
    outstanding_dct_amount_more_than_9_months_usd = serializers.FloatField(read_only=True)
    core_value_assessment_expiring = serializers.DurationField(read_only=True)

    class Meta:
        model = PartnerOrganization
        fields = (
            'id',
            'name',
            'sections',
            'locations',
            'action_points',
            'total_ct_cp',
            'total_ct_ytd',
            'outstanding_dct_amount_6_to_9_months_usd',
            'outstanding_dct_amount_more_than_9_months_usd',
            'vendor_number',
            'partner_type',
            'core_value_assessment_expiring',
        )


class PartnerOrganizationCreateUpdateSerializer(SnapshotModelSerializer):
    name = serializers.CharField(source='organization.name', read_only=True)
    vendor_number = serializers.CharField(source='organization.vendor_number', read_only=True)
    short_name = serializers.CharField(source='organization.short_name', read_only=True)
    partner_type = serializers.CharField(source='organization.organization_type', read_only=True)
    cso_type = serializers.CharField(source='organization.cso_type', read_only=True)
    staff_members = PartnerStaffMemberNestedSerializer(many=True, read_only=True)
    planned_engagement = PlannedEngagementNestedSerializer(read_only=True)
    hidden = serializers.BooleanField(read_only=True)
    planned_visits = PartnerPlannedVisitsSerializer(many=True, read_only=True, required=False)
    core_values_assessments = CoreValuesAssessmentSerializer(many=True, read_only=True, required=False)
    monitoring_activity_groups = MonitoringActivityGroupSerializer(required=False)

    def validate(self, data):
        data = super().validate(data)

        type_of_assessment = data.get('type_of_assessment', self.instance.type_of_assessment)
        rating = data.get('rating', self.instance.rating)
        basis_for_risk_rating = data.get('basis_for_risk_rating', self.instance.basis_for_risk_rating)

        if basis_for_risk_rating and \
                type_of_assessment in [PartnerOrganization.HIGH_RISK_ASSUMED, PartnerOrganization.LOW_RISK_ASSUMED]:
            raise ValidationError(
                {'basis_for_risk_rating': 'The basis for risk rating has to be blank if Type is Low or High'})

        if basis_for_risk_rating and \
                rating == PartnerOrganization.RATING_NOT_REQUIRED and \
                type_of_assessment == PartnerOrganization.MICRO_ASSESSMENT:
            raise ValidationError({
                'basis_for_risk_rating':
                    'The basis for risk rating has to be blank if rating is Not Required and type is Micro Assessment'
            })

        return data

    def save_monitoring_activity_groups(self, instance, groups):
        instance_groups = list(instance.monitoring_activity_groups.prefetch_related('monitoring_activities'))
        updated = False

        for i in range(len(groups)):
            if i >= len(instance_groups):
                group_object = MonitoringActivityGroup.objects.create(partner=instance)
                instance_activities = []
            else:
                group_object = instance_groups[i]
                instance_activities = instance_groups[i].monitoring_activities.all()

            if set(instance_activities).symmetric_difference(set(groups[i])):
                updated = True

            group_object.monitoring_activities.set(groups[i])

        if len(instance_groups) > len(groups):
            updated = True

            for i in range(len(groups), len(instance_groups)):
                instance_groups[i].delete()

        return updated

    def update(self, instance, validated_data):
        monitoring_activity_groups = validated_data.pop('monitoring_activity_groups', None)

        instance = super().update(instance, validated_data)

        if monitoring_activity_groups is not None:
            groups_updated = self.save_monitoring_activity_groups(instance, monitoring_activity_groups)
            if groups_updated:
                instance.update_programmatic_visits()

        return instance

    class Meta:
        model = PartnerOrganization
        fields = "__all__"
        extra_kwargs = {
            "partner_type": {
                "error_messages": {
                    "null": 'Vendor number must belong to PRG2 account group'
                }
            }
        }


class PartnerOrganizationHactSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='organization.name')
    vendor_number = serializers.CharField(source='organization.vendor_number')
    short_name = serializers.CharField(source='organization.short_name')
    partner_type = serializers.CharField(source='organization.organization_type')
    cso_type = serializers.CharField(source='organization.cso_type')
    planned_engagement = PlannedEngagementSerializer(read_only=True)
    hact_min_requirements = serializers.JSONField()
    rating = serializers.CharField(source='get_rating_display')

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
