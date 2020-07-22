from rest_framework import serializers
from unicef_restlib.fields import SeparatedReadWriteField

from etools.applications.partners.models import InterventionResultLink
from etools.applications.reports.models import LowerResult, Result, ResultType


class InterventionLowerResultSerializer(serializers.ModelSerializer):
    cp_output = SeparatedReadWriteField(
        read_field=serializers.IntegerField(),
        write_field=serializers.PrimaryKeyRelatedField(
            queryset=Result.objects.filter(result_type__name=ResultType.OUTPUT),
            allow_null=True, required=False,
        ),
        source='result_link.cp_output_id',
        allow_null=True,
    )

    class Meta:
        model = LowerResult
        fields = ('id', 'name', 'code', 'cp_output')

    def create(self, validated_data):
        cp_output = validated_data.pop('result_link', {}).get('cp_output_id', None)
        result_link = InterventionResultLink.objects.get_or_create(
            intervention=self.context['intervention'], cp_output=cp_output
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
                intervention=self.context['intervention'],
                cp_output=cp_output
            ).first()
            if result_link and result_link != instance.result_link:
                old_link, instance.result_link = instance.result_link, result_link
                instance.save()
                if old_link.cp_output is None:
                    # just temp link, can be safely removed
                    old_link.delete()
        elif cp_output is None and 'cp_output_id' in result_link_data:
            if instance.result_link.cp_output is not None:
                instance.result_link = InterventionResultLink.objects.create(
                    intervention=self.context['intervention'], cp_output=None
                )
                instance.save()

        return instance
