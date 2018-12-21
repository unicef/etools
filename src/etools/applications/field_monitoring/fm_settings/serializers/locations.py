import json

from django.contrib.gis.db.models import Collect
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from unicef_locations.serializers import LocationSerializer, LocationLightSerializer

from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.applications.permissions_simplified.serializers import SafeReadOnlySerializerMixin


class LocationCountrySerializer(LocationLightSerializer):
    point = serializers.SerializerMethodField()

    class Meta(LocationLightSerializer.Meta):
        fields = LocationLightSerializer.Meta.fields + ('point', )

    def get_point(self, obj):
        point = obj.point or self.Meta.model.objects.aggregate(boundary=Collect('point'))['boundary'].centroid
        return json.loads(point.json)


class LocationSiteLightSerializer(SafeReadOnlySerializerMixin, serializers.ModelSerializer):
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


class LocationSiteSerializer(LocationSiteLightSerializer):
    parent = LocationSerializer(read_only=True)

    class Meta(LocationSiteLightSerializer.Meta):
        pass
