
from rest_framework import serializers

from .models import CartoDBTable, GatewayType, Location, Governorate, Region, Locality


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


class GovernorateSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Governorate
        fields = (
            'id',
            'name',
            'p_code',
            'gateway',
            'color',
            'geom',
        )


class RegionSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Region
        fields = (
            'id',
            'name',
            'p_code',
            'gateway',
            'color',
            'geom',
            'governorate'
        )

class LocalitySerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Locality
        fields = (
            'id',
            'region',
            'cad_code',
            'cas_code',
            'cas_code_un',
            'name',
            'cas_village_name',
            'p_code',
            'gateway',
            'geom',
            'color'
        )


class LocationSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Location
        fields = (
            'id',
            'name',
            'p_code',
            'gateway',
            'locality',
            'point',
            'latitude',
            'longitude'
        )
