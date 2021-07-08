from rest_framework import serializers

from etools.applications.eface.models import EFaceForm, FormActivity


class EFaceFormSerializer(serializers.ModelSerializer):
    actions_available = serializers.SerializerMethodField()

    class Meta:
        model = EFaceForm
        fields = '__all__'  # todo: replace with fields list

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

        if obj.status == EFaceForm.STATUSES.submitted:
            if self._is_programme_officer(obj, user):
                available_actions.append('approve')
                available_actions.append('reject')

        # temporary actions
        if obj.status == EFaceForm.STATUSES.unicef_approved:
            if self._is_programme_officer(obj, user):
                available_actions.append('transaction_approve')
                available_actions.append('transaction_reject')

        if obj.status in [
            EFaceForm.STATUSES.draft,
            EFaceForm.STATUSES.submitted,
            EFaceForm.STATUSES.unicef_approved,
        ]:
            if self._is_programme_officer(obj, user):
                available_actions.append('cancel')

        return [action for action in default_ordering if action in available_actions]

    # todo: make cached
    def _is_partner_user(self, obj, user):
        # todo: update on responsible officers implementation
        return obj.intervention.partner_focal_points.filter(email=user.email).exists()

    # todo: make cached
    def _is_programme_officer(self, obj, user):
        return obj.intervention.unicef_focal_points.filter(email=user.email).exists()


class FormActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = FormActivity
        fields = (
            'id',
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
