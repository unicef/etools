from __future__ import unicode_literals

import six
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from et2f.serializers import TravelListSerializer


class SearchFilterSerializer(serializers.Serializer):
    reverse = serializers.BooleanField(required=False, default=False)
    search = serializers.CharField(required=False, default='')


class ShowHiddenFilterSerializer(serializers.Serializer):
    show_hidden = serializers.BooleanField(required=False, default=False)


class SortFilterSerializer(serializers.Serializer):
    _SORTABLE_FIELDS = tuple(TravelListSerializer.Meta.fields)
    sort_by = serializers.CharField(default=_SORTABLE_FIELDS[0])

    def validate_sort_by(self, value):
        if value not in self._SORTABLE_FIELDS:
            valid_values = ', '.join(self._SORTABLE_FIELDS)
            raise ValidationError('Invalid sorting option. Valid values are {}'.format(valid_values))
        return value


class FilterBoxFilterSerializer(serializers.Serializer):
    f_traveler = serializers.IntegerField(source='traveller__pk')
    f_supervisor = serializers.IntegerField(source='supervisor__pk')
    f_year = serializers.IntegerField(source='year')
    f_month = serializers.IntegerField(source='month')
    f_office = serializers.IntegerField(source='offices__pk')
    f_section = serializers.IntegerField(source='sections__pk')
    f_travel_type = serializers.CharField(source='travel_type')
    f_status = serializers.CharField(source='status')
    f_partner = serializers.IntegerField(source='travel_activity__partner__pk')
    f_cp_output = serializers.IntegerField(source='cp_output')

    # TODO simon: figure out how to handle when year is not in the payload but month is

    def to_internal_value(self, data):
        data = super(FilterBoxFilterSerializer, self).to_internal_value(data)

        # Adjust month because frontend sends 0-11
        if 'month' in data:
            data['month'] += 1

        return data