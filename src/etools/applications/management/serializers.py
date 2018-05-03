
from django.contrib.gis.geos import GEOSGeometry

from rest_framework import serializers

from etools.applications.locations.models import Location


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
        return "{}".format(GEOSGeometry(obj.geom).wkt if obj.geom else '')

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
