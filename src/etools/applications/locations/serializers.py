from rest_framework import serializers
from unicef_locations.utils import get_location_model


class LocationExportFlatSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_location_model()
        exclude = ('created', 'modified', 'tree_id', 'lft', 'rght', 'level')
