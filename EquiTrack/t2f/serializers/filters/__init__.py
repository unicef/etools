from __future__ import unicode_literals

from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class SearchFilterSerializer(serializers.Serializer):
    search = serializers.CharField(default='', required=False)


class SortFilterSerializer(serializers.Serializer):
    _SORTABLE_FIELDS = ()
    reverse = serializers.BooleanField(default=False, required=False)
    sort_by = serializers.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(SortFilterSerializer, self).__init__(*args, **kwargs)
        if self._SORTABLE_FIELDS:
            self.fields['sort_by'].default = self._SORTABLE_FIELDS[0]

    def validate_sort_by(self, value):
        if value not in self._SORTABLE_FIELDS:
            valid_values = ', '.join(self._SORTABLE_FIELDS)
            raise ValidationError('Invalid sorting option. Valid values are {}'.format(valid_values))
        return value
