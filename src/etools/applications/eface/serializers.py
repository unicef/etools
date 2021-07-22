import datetime

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from unicef_restlib.fields import SeparatedReadWriteField

from etools.applications.eface.models import EFaceForm, FormActivity
from etools.applications.eface.validation.permissions import EFaceFormPermissions
from etools.applications.partners.serializers.interventions_v3 import InterventionDetailSerializer
from etools.applications.users.serializers_v3 import MinimalUserSerializer


class CustomInterventionDetailSerializer(InterventionDetailSerializer):
    # hack to exclude extra fields
    permissions = None
    available_actions = None

    class Meta(InterventionDetailSerializer.Meta):
        fields = [
            field for field in InterventionDetailSerializer.Meta.fields
            if field not in ['permissions', 'available_actions']
        ]


class MonthYearDateField(serializers.Field):
    default_error_messages = {
        'unknown_type': _('Unknown input type. String required.'),
        'invalid': _('Date has wrong format. Required format: mm/yyyy.'),
    }

    def to_internal_value(self, data):
        if isinstance(data, datetime.date):
            return data

        if not isinstance(data, str):
            self.fail('unknown_type')

        try:
            value = datetime.datetime.strptime(data, '%m%Y')
        except ValueError:
            self.fail('invalid')

        return value.replace(day=1).date()

    def to_representation(self, value):
        return value.strftime('%m%Y')


class EFaceFormListSerializer(serializers.ModelSerializer):
    authorized_amount_date_start = MonthYearDateField(required=False)
    authorized_amount_date_end = MonthYearDateField(required=False)
    requested_amount_date_start = MonthYearDateField(required=False)
    requested_amount_date_end = MonthYearDateField(required=False)

    class Meta:
        model = EFaceForm
        fields = (
            'id',
            'reference_number',
            'title',
            'status',
            'intervention',
            'request_type',
            'request_represents_expenditures',
            'expenditures_disbursed',
            'notes',
            'submitted_by',
            'submitted_by_unicef_date',
            'authorized_amount_date_start',
            'authorized_amount_date_end',
            'requested_amount_date_start',
            'requested_amount_date_end',
            'date_submitted',
            'date_rejected',
            'date_pending',
            'date_approved',
            'date_closed',
            'date_cancelled',
            'rejection_reason',
            'transaction_rejection_reason',
            'cancel_reason',
            'reporting_authorized_amount',
            'reporting_actual_project_expenditure',
            'reporting_expenditures_accepted_by_agency',
            'reporting_balance',
            'requested_amount',
            'requested_authorized_amount',
            'requested_outstanding_authorized_amount',
        )
        read_only_fields = (
            'reporting_authorized_amount',
            'reporting_actual_project_expenditure',
            'reporting_expenditures_accepted_by_agency',
            'reporting_balance',
            'requested_amount',
            'requested_authorized_amount',
            'requested_outstanding_authorized_amount',
        )


class FormActivitySerializer(serializers.ModelSerializer):
    default_error_messages = {
        'pd_activity_required': _('PD Activity is required'),
        'eepm_kind_required': _('EEPM kind is required'),
        'description_required': _('Description is required'),
    }

    class Meta:
        model = FormActivity
        fields = (
            'id',
            'kind',
            'pd_activity',
            'eepm_kind',
            'description',
            'coding',
            'reporting_authorized_amount',
            'reporting_actual_project_expenditure',
            'reporting_expenditures_accepted_by_agency',
            'reporting_balance',
            'requested_amount',
            'requested_authorized_amount',
            'requested_outstanding_authorized_amount',
        )
        read_only_fields = (
            'reporting_balance',
            'requested_outstanding_authorized_amount',
        )

    def validate(self, validated_data):
        validated_data = super().validate(validated_data)
        if 'kind' in validated_data:
            kind = validated_data['kind']
            if kind == FormActivity.KIND_CHOICES.activity:
                if 'pd_activity' not in validated_data:
                    self.fail('pd_activity_required')
            elif kind == FormActivity.KIND_CHOICES.eepm:
                if 'eepm_kind' not in validated_data:
                    self.fail('eepm_kind_required')
            elif kind == FormActivity.KIND_CHOICES.custom:
                if 'description' not in validated_data:
                    self.fail('description_required')

        return validated_data


class EFaceFormSerializer(EFaceFormListSerializer):
    actions_available = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    intervention = SeparatedReadWriteField(read_field=CustomInterventionDetailSerializer())
    submitted_by = SeparatedReadWriteField(read_field=MinimalUserSerializer())
    activities = FormActivitySerializer(many=True)

    class Meta(EFaceFormListSerializer.Meta):
        fields = EFaceFormListSerializer.Meta.fields + (
            'actions_available',
            'permissions',
            'activities',
        )

    def get_permissions(self, obj):
        user = self.context['request'].user
        ps = EFaceForm.permission_structure()
        permissions = EFaceFormPermissions(
            user=user,
            instance=self.instance,
            permission_structure=ps,
        )
        return permissions.get_permissions()

    def get_actions_available(self, obj):
        default_ordering = [
            'submit',
            'approve',
            'reject',
            'transaction_approve',
            'transaction_approve',
            'cancel',
        ]
        available_actions = [
            # todo:
            # "download_comments",
            # "export",
            # "generate_pdf",
        ]
        user = self.context['request'].user

        if obj.status == EFaceForm.STATUSES.draft:
            if self._is_partner_user(obj, user):
                available_actions.append('submit')
                available_actions.append('cancel')
            if self._is_programme_officer(obj, user):
                available_actions.append('cancel')

        if obj.status == EFaceForm.STATUSES.submitted:
            if self._is_programme_officer(obj, user):
                available_actions.append('send_to_vision')
                available_actions.append('reject')

        # temporary actions
        if obj.status == EFaceForm.STATUSES.pending:
            if self._is_programme_officer(obj, user):
                available_actions.append('transaction_approve')
                available_actions.append('transaction_reject')

        if obj.status in [
            EFaceForm.STATUSES.draft,
            EFaceForm.STATUSES.rejected,
        ]:
            if self._is_programme_officer(obj, user) or self._is_partner_user(obj, user):
                available_actions.append('cancel')

        return [action for action in default_ordering if action in available_actions]

    # todo: make cached
    def _is_partner_user(self, obj, user):
        # todo: update on responsible officers implementation
        return obj.intervention.partner_focal_points.filter(email=user.email).exists()

    # todo: make cached
    def _is_programme_officer(self, obj, user):
        return obj.intervention.unicef_focal_points.filter(email=user.email).exists()
