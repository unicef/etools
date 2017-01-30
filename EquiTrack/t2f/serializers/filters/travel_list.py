from __future__ import unicode_literals

from rest_framework import serializers

from t2f.serializers import TravelListSerializer
from t2f.serializers.filters import SortFilterSerializer


class ShowHiddenFilterSerializer(serializers.Serializer):
    show_hidden = serializers.BooleanField(default=False, required=False)


class TravelSortFilterSerializer(SortFilterSerializer):
    _SORTABLE_FIELDS = tuple(TravelListSerializer.Meta.fields)


class TravelFilterBoxSerializer(serializers.Serializer):
    f_traveler = serializers.IntegerField(source='traveler__pk', required=False)
    f_supervisor = serializers.IntegerField(source='supervisor__pk', required=False)
    f_year = serializers.IntegerField(source='year', required=False)
    f_month = serializers.IntegerField(source='month', required=False)
    f_office = serializers.IntegerField(source='office__pk', required=False)
    f_section = serializers.IntegerField(source='section__pk', required=False)
    f_travel_type = serializers.CharField(source='mode_of_travel__contains', required=False)
    f_status = serializers.CharField(source='status', required=False)
    f_partner = serializers.IntegerField(source='activities__partner__pk', required=False)
    f_cp_output = serializers.IntegerField(source='cp_output', required=False)

    # TODO simon: figure out how to handle when year is not in the payload but month is

    def to_internal_value(self, data):
        data = super(TravelFilterBoxSerializer, self).to_internal_value(data)

        # Adjust month because frontend sends 0-11
        if 'month' in data:
            data['month'] += 1

        # Mode of travel is an array field and the lookup has to be a list
        if 'mode_of_travel__contains' in data:
            data['mode_of_travel__contains'] = [data['mode_of_travel__contains']]

        return data
