from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from etools.applications.field_monitoring.models import MethodType
from etools.applications.field_monitoring_shared.models import Method


class MethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Method
        fields = ('id', 'name', 'is_types_applicable')


class MethodTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MethodType
        fields = ('id', 'method', 'name', 'is_recommended')

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        if not validated_data['method'].is_types_applicable:
            raise ValidationError({'method', _('Unable to add type for this Method')})

        return validated_data
