from __future__ import unicode_literals

import six
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from t2f.serializers import TravelListSerializer


class SearchFilterSerializer(serializers.Serializer):
    search = serializers.CharField(default='', required=False)


class ShowHiddenFilterSerializer(serializers.Serializer):
    show_hidden = serializers.BooleanField(default=False, required=False)


class SortFilterSerializer(serializers.Serializer):
    _SORTABLE_FIELDS = tuple(TravelListSerializer.Meta.fields)
    reverse = serializers.BooleanField(default=False, required=False)
    sort_by = serializers.CharField(default=_SORTABLE_FIELDS[0], required=False)

    def validate_sort_by(self, value):
        if value not in self._SORTABLE_FIELDS:
            valid_values = ', '.join(self._SORTABLE_FIELDS)
            raise ValidationError('Invalid sorting option. Valid values are {}'.format(valid_values))
        return value


class FilterBoxFilterSerializer(serializers.Serializer):
    f_traveler = serializers.IntegerField(source='traveler__pk', required=False)
    f_supervisor = serializers.IntegerField(source='supervisor__pk', required=False)
    f_year = serializers.IntegerField(source='year', required=False)
    f_month = serializers.IntegerField(source='month', required=False)
    f_office = serializers.IntegerField(source='office__pk', required=False)
    f_section = serializers.IntegerField(source='section__pk', required=False)
    f_travel_type = serializers.CharField(source='mode_of_travel__id', required=False)
    f_status = serializers.CharField(source='status', required=False)
    f_partner = serializers.IntegerField(source='activities__partner__pk', required=False)
    f_cp_output = serializers.IntegerField(source='cp_output', required=False)

    # TODO simon: figure out how to handle when year is not in the payload but month is

    def to_internal_value(self, data):
        data = super(FilterBoxFilterSerializer, self).to_internal_value(data)

        # Adjust month because frontend sends 0-11
        if 'month' in data:
            data['month'] += 1

        return data
