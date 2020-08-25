from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_restlib.fields import SeparatedReadWriteField

from etools.applications.partners.models import InterventionResultLink
from etools.applications.reports.models import LowerResult, Result, ResultType


class InterventionLowerResultBaseSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True
        model = LowerResult
        fields = ('id', 'name', 'code')


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
