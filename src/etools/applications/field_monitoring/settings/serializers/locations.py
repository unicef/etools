from rest_framework import serializers

from unicef_locations.serializers import LocationSerializer

from etools.applications.field_monitoring.settings.models import LocationSite


class LocationSiteLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationSite
        fields = ['id', 'name', 'p_code', 'parent', 'point', 'security_detail', 'is_active']
        extra_kwargs = {
            'point': {'required': True},
        }


class LocationSiteSerializer(LocationSiteLightSerializer):
    parent = LocationSerializer(read_only=True)

    class Meta(LocationSiteLightSerializer.Meta):
        pass
