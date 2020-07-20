from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_restlib.fields import SeparatedReadWriteField

from etools.applications.reports.models import LowerResult, ResultType, Result


class InterventionLowerResultSerializer(serializers.ModelSerializer):
    cp_output = SeparatedReadWriteField(
        read_field=serializers.IntegerField(),
        write_field=serializers.PrimaryKeyRelatedField(
            queryset=Result.objects.filter(result_type__name=ResultType.OUTPUT),
            required=False,
        ),
        source='result_link.cp_output_id',
        allow_null=True,
    )

    class Meta:
        model = LowerResult
        fields = ('id', 'name', 'code', 'cp_output')

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        result_link_data = validated_data.pop('result_link', None)
        if result_link_data:
            intervention = self.context['intervention']
            result_link = intervention.result_links.filter(cp_output=result_link_data['cp_output_id']).first()
            if not result_link:
                raise ValidationError({'cp_output': [_('Selected output is not linked to the intervention.')]})
            validated_data['result_link'] = result_link
        else:
            if not self.partial:
                validated_data['result_link'] = None

        return validated_data
