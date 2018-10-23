from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework.exceptions import ValidationError

from unicef_locations.models import Location
from unicef_locations.serializers import LocationSerializer

from etools.applications.field_monitoring.settings.models import Site


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
