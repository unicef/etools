from rest_framework import serializers
from rest_framework_gis.serializers import GeometryField
from unicef_locations.utils import get_location_model


class LocationExportFlatSerializer(serializers.ModelSerializer):
    parent_p_code = serializers.CharField(source='parent_pcode', default=None)
    geom = GeometryField(precision=5, remove_duplicates=True)

    class Meta:
        model = get_location_model()
        fields = ('id', 'name', 'p_code', 'admin_level', 'admin_level_name', 'point', 'geom', 'parent_p_code')
