
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


class LocationSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = Location
        fields = (
            'id',
            'name',
            'gateway',
            'point'
        )
