from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_locations.models import Location
from unicef_locations.serializers import LocationSerializer

from etools.applications.field_monitoring.models import MethodType, Site
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


class FMLocationSerializer(LocationSerializer):
    class Meta:
        model = Location
        fields = LocationSerializer.Meta.fields + ('geom',)


class SiteSerializer(LocationSerializer):
    name = None  # use builtin field for name

    class Meta(LocationSerializer.Meta):
        model = Site
        fields = list(LocationSerializer.Meta.fields) + ['point', 'security_detail', 'is_active']
        fields.remove('gateway')
        extra_kwargs = {
            'parent': {'required': True},
            'point': {'required': True},
        }

    def validate_parent(self, parent):
        if not parent:
            self.fail('required')

        try:
            self.Meta.model.clean_parent(parent)
        except DjangoValidationError as ex:
            raise ValidationError(ex.message)

        return parent
