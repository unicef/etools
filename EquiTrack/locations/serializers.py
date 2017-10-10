from __future__ import unicode_literals

from rest_framework import serializers

from .models import CartoDBTable, GatewayType, Location


class CartoDBTableSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = CartoDBTable
        fields = (
            'id',
            'domain',
            'api_key',
            'table_name',
            'display_name',
            'pcode_col',
            'color',
            'location_type',
            'name_col'
        )


class GatewayTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = GatewayType
        fields = '__all__'


class LocationSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    location_type = serializers.CharField(source='gateway.name')
    location_type_admin_level = serializers.IntegerField(source='gateway.admin_level')
    geo_point = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    def get_geo_point(self, obj):
        return "{}".format(obj.geo_point)

    def get_name(self, obj):
        return '{} [{} - {}]'.format(obj.name, obj.gateway.name, obj.p_code)

    class Meta:
        model = Location
        fields = (
            'id',
            'name',
            'p_code',
            'location_type',
            'location_type_admin_level',
            'parent',
            'geo_point',
        )


class LocationLightSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return '{} [{} - {}]'.format(obj.name, obj.gateway.name, obj.p_code)

    class Meta:
        model = Location
        fields = (
            'id',
            'name',
            'p_code',
        )


class LocationExportSerializer(serializers.ModelSerializer):
    location_type = serializers.CharField(source='gateway.name')
    geo_point = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = (
            'id',
            'name',
            'p_code',
            'location_type',
            'parent',
            'geo_point',
            'latitude',
            'longitude',
        )


class LocationExportFlatSerializer(serializers.ModelSerializer):
    location_type = serializers.CharField(source='gateway.name')
    geom = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = (
            'id',
            'name',
            'p_code',
            'location_type',
            'parent',
            'geom',
            'point',
            'latitude',
            'longitude',
        )

    def get_geom(self, obj):
        return obj.geom.point_on_surface if obj.geom else ""
