
from rest_framework.serializers import ModelSerializer

from .models import CartoDBTable, Location


class CartoDBTableSerializer(ModelSerializer):

    class Meta:
        model = CartoDBTable
        fields = (
            'domain',
            'api_key',
            'table_name',
            'display_name',
            'pcode_col',
            'color',
        )
class LocationSerializer(ModelSerializer):

    class Meta:
        model = Location
        fields = (
            'id',
            'name',
        )