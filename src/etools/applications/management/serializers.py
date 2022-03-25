from django.contrib.gis.geos import GEOSGeometry

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from etools.applications.locations.models import Location


class GisLocationListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Location
        fields = (
            'id',
            'parent_id',
            'name',
            'p_code',
            'level',
        )


class GisLocationWktSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    geom = serializers.SerializerMethodField()
    point = serializers.SerializerMethodField()

    def get_geom(self, obj):
        return "{}".format(GEOSGeometry(obj.geom).wkt if obj.geom else '')

    def get_point(self, obj):
        return "{}".format(GEOSGeometry(obj.point) if obj.point else '')

    class Meta:
        model = Location
        geo_field = None
        fields = (
            'id',
            'parent_id',
            'name',
            'p_code',
            'level',
            'geom',
            'point'
        )


class GisLocationGeojsonSerializer(GeoFeatureModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Location
        geo_field = None
        fields = (
            'id',
            'parent_id',
            'name',
            'p_code',
            'level',
            'geom',
            'point'
        )
