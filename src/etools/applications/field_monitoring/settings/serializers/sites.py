from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from unicef_locations.serializers import LocationSerializer, LocationLightSerializer

from etools.applications.field_monitoring.settings.models import LocationSite


class LocationCountrySerializer(LocationLightSerializer):
    class Meta(LocationLightSerializer.Meta):
        fields = LocationLightSerializer.Meta.fields + (
            'geom', 'point',
        )


class LocationSiteSerializer(serializers.ModelSerializer):
    parent = LocationSerializer(read_only=True)
    is_active = serializers.ChoiceField(choices=(
        (True, _('Active')),
        (False, _('Inactive')),
    ), label=_('Status'), required=False)

    class Meta:
        model = LocationSite
        fields = ['id', 'name', 'p_code', 'parent', 'point', 'security_detail', 'is_active']
        extra_kwargs = {
            'point': {'required': True},
        }
