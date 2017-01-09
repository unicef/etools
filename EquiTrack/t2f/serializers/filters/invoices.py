from __future__ import unicode_literals

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from t2f.serializers import ActionPointSerializer


class SearchFilterSerializer(serializers.Serializer):
    search = serializers.CharField(default='', required=False)


class SortFilterSerializer(serializers.Serializer):
    _SORTABLE_FIELDS = tuple(ActionPointSerializer.Meta.fields)
    reverse = serializers.BooleanField(default=False, required=False)
    sort_by = serializers.CharField(default=_SORTABLE_FIELDS[0], required=False)

    def validate_sort_by(self, value):
        if value not in self._SORTABLE_FIELDS:
            valid_values = ', '.join(self._SORTABLE_FIELDS)
            raise ValidationError('Invalid sorting option. Valid values are {}'.format(valid_values))
        return value


class FilterBoxFilterSerializer(serializers.Serializer):
    f_vendor_number = serializers.CharField(source='vendor_number', required=False)
    f_status = serializers.CharField(source='status', required=False)
