from __future__ import unicode_literals

from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class SearchFilterSerializer(serializers.Serializer):
    search = serializers.CharField(default='', required=False)


class SortFilterSerializer(serializers.Serializer):
    SORT_BY_SERIALIZER = None
    reverse = serializers.BooleanField(default=False, required=False)
    sort_by = serializers.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(SortFilterSerializer, self).__init__(*args, **kwargs)
        if self.SORT_BY_SERIALIZER:
            self._sortable_fields = tuple(self.SORT_BY_SERIALIZER.Meta.fields)
            self.fields['sort_by'].default = self._sortable_fields[0]
        else:
            self._sortable_fields = ()

    def validate_sort_by(self, value):
        if value not in self._sortable_fields:
            valid_values = ', '.join(self._sortable_fields)
            raise ValidationError('Invalid sorting option. Valid values are {}'.format(valid_values))
        return value

    def to_internal_value(self, data):
        attrs = super(SortFilterSerializer, self).to_internal_value(data)
        if 'sort_by' in attrs:
            sort_by = attrs['sort_by']
            source = self.SORT_BY_SERIALIZER().fields[sort_by].source
            attrs['sort_by'] = source.replace('.', '__')
        return attrs
