from __future__ import unicode_literals

from rest_framework import serializers
from django.contrib.gis.geos import GEOSGeometry

from locations.models import Location


class GisLocationListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Location
        fields = (
            'id',
            'name',
            'p_code',
            'gateway_id',
            'level',
        )


class GisLocationGeoDetailSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    geom = serializers.SerializerMethodField()

    def get_geom(self, obj):
        geo_format = self.context.get('request').query_params.get('geo_format') or None

        if geo_format == 'wkt':
            return "{}".format(GEOSGeometry(obj.geom).wkt if obj.geom else '')
        else:
            return "{}".format(GEOSGeometry(obj.geom).geojson if obj.geom else '')

    class Meta:
        model = Location
        fields = (
            'id',
            'name',
            'p_code',
            'gateway_id',
            'level',
            'geom'
        )
