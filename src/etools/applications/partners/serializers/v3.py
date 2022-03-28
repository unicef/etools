from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_restlib.fields import SeparatedReadWriteField

from etools.applications.partners.models import InterventionResultLink, InterventionReview, PRCOfficerInterventionReview
from etools.applications.reports.models import LowerResult, Result, ResultType
from etools.applications.users.serializers_v3 import MinimalUserSerializer


class CPOutputValidator:
    set_context = True

    def set_context(self, field):
        self.intervention = field.parent.intervention

    def __call__(self, value):
        # check that value provided matches allowed options
        cp_output_qs = InterventionResultLink.objects.filter(
            intervention=self.intervention,
            cp_output=value,
        )
        if not cp_output_qs.exists():
            raise serializers.ValidationError(_("Invalid CP Output provided."))


class InterventionLowerResultBaseSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True
        model = LowerResult
        fields = ('id', 'name', 'code', 'total')
        extra_kwargs = {
            'code': {'required': False},
        }


class InterventionReviewSerializer(serializers.ModelSerializer):
    created_date = serializers.DateField(read_only=True)
    submitted_by = MinimalUserSerializer(read_only=True)
    overall_approver = SeparatedReadWriteField(read_field=MinimalUserSerializer())

    class Meta:
        model = InterventionReview
        fields = (
            'id',
            'amendment',
            'review_type',
            'created_date',
            'submitted_by',
            'review_date',

            'meeting_date',
            'prc_officers',
            'overall_approver',

            'relationship_is_represented',
            'partner_comparative_advantage',
            'relationships_are_positive',
            'pd_is_relevant',
            'pd_is_guided',
            'ges_considered',
            'budget_is_aligned',
            'supply_issues_considered',

            'overall_comment',
            'actions_list',
            'overall_approval',
            'sent_back_comment',
        )
        read_only_fields = (
            'amendment', 'review_type', 'overall_approval', 'sent_back_comment',
        )

    def update(self, instance, validated_data):
        self._update_prc_officers(instance, validated_data)
        return super().update(instance, validated_data)

    def _update_prc_officers(self, instance, validated_data):
        new_prc_officers = validated_data.pop('prc_officers', None)
        if new_prc_officers is None:
            return

        original_prc_officers = instance.prc_officers.all()
        diff = set(original_prc_officers) - set(new_prc_officers)
        instance.prc_officers.add(*new_prc_officers)
        instance.prc_officers.remove(*diff)


class PRCOfficerInterventionReviewSerializer(serializers.ModelSerializer):
    user = MinimalUserSerializer(read_only=True)

    class Meta:
        model = PRCOfficerInterventionReview
        fields = (
            'id',
            'user',

            'relationship_is_represented',
            'partner_comparative_advantage',
            'relationships_are_positive',
            'pd_is_relevant',
            'pd_is_guided',
            'ges_considered',
            'budget_is_aligned',
            'supply_issues_considered',

            'overall_comment',
            'overall_approval',
            'review_date',
        )
        read_only_fields = (
            'review_date',
        )

    def update(self, instance, validated_data):
        if validated_data.get('overall_approval') is not None:
            validated_data['review_date'] = timezone.now().date()
        return super().update(instance, validated_data)


class PartnerInterventionLowerResultSerializer(InterventionLowerResultBaseSerializer):
    cp_output = serializers.ReadOnlyField(source='result_link.cp_output_id')

    class Meta(InterventionLowerResultBaseSerializer.Meta):
        fields = InterventionLowerResultBaseSerializer.Meta.fields + ('cp_output',)

    def __init__(self, *args, **kwargs):
        self.intervention = kwargs.pop('intervention', None)
        super().__init__(*args, **kwargs)

    def save(self, **kwargs):
        if not self.intervention:
            raise ValidationError(_('Unknown intervention.'))
        return super().save(**kwargs)

    def create(self, validated_data):
        result_link = InterventionResultLink.objects.create(intervention=self.intervention, cp_output=None)
        validated_data['result_link'] = result_link

        instance = super().create(validated_data)
        return instance


class UNICEFInterventionLowerResultSerializer(InterventionLowerResultBaseSerializer):
    cp_output = SeparatedReadWriteField(
        read_field=serializers.ReadOnlyField(),
        write_field=serializers.PrimaryKeyRelatedField(
            queryset=Result.objects.filter(result_type__name=ResultType.OUTPUT),
            allow_null=True, required=False,
        ),
        source='result_link.cp_output_id',
        allow_null=True,
        validators=[CPOutputValidator()],
    )

    class Meta(InterventionLowerResultBaseSerializer.Meta):
        fields = InterventionLowerResultBaseSerializer.Meta.fields + ('cp_output',)

    def __init__(self, *args, **kwargs):
        self.intervention = kwargs.pop('intervention', None)
        super().__init__(*args, **kwargs)

    def save(self, **kwargs):
        if not self.intervention:
            raise ValidationError(_('Unknown intervention.'))
        return super().save(**kwargs)

    def create(self, validated_data):
        cp_output = validated_data.pop('result_link', {}).get('cp_output_id', None)
        result_link = InterventionResultLink.objects.get_or_create(
            intervention=self.intervention, cp_output=cp_output
        )[0]
        validated_data['result_link'] = result_link

        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        result_link_data = validated_data.pop('result_link', {})
        cp_output = result_link_data.get('cp_output_id', None)
        instance = super().update(instance, validated_data)
        if cp_output:
            # recreate result link from one with empty cp output if data is sufficient
            result_link = InterventionResultLink.objects.filter(
                intervention=self.intervention,
                cp_output=cp_output
            ).first()
            if result_link and result_link != instance.result_link:
                old_link, instance.result_link = instance.result_link, result_link
                instance.save()
                if old_link.cp_output is None and not old_link.ll_results.exclude(pk=instance.pk).exists():
                    # just temp link, can be safely removed
                    old_link.delete()
        elif cp_output is None and 'cp_output_id' in result_link_data:
            if instance.result_link.cp_output is not None:
                instance.result_link = InterventionResultLink.objects.create(
                    intervention=self.intervention, cp_output=None
                )
                instance.save()

        return instance
