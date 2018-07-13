
from rest_framework import serializers

from etools.applications.t2f.serializers.filters import SortFilterSerializer
from etools.applications.t2f.serializers.travel import TravelListSerializer


class ShowHiddenFilterSerializer(serializers.Serializer):
    show_hidden = serializers.BooleanField(default=False, required=False)


class TravelSortFilterSerializer(SortFilterSerializer):
    SORT_BY_SERIALIZER = TravelListSerializer


class TravelFilterBoxSerializer(serializers.Serializer):
    f_traveler = serializers.IntegerField(source='traveler__pk', required=False)
    f_supervisor = serializers.IntegerField(source='supervisor__pk', required=False)
    f_year = serializers.IntegerField(source='year', required=False)
    f_month = serializers.IntegerField(source='month', required=False)
    f_office = serializers.IntegerField(source='office__pk', required=False)
    f_section = serializers.IntegerField(source='section__pk', required=False)
    f_travel_type = serializers.CharField(source='activities__travel_type', required=False)
    f_status = serializers.CharField(source='status', required=False)
    f_partner = serializers.IntegerField(source='activities__partner__pk', required=False)
    f_location = serializers.IntegerField(source='activities__locations__pk', required=False)
    f_cp_output = serializers.IntegerField(source='cp_output', required=False)

    def to_internal_value(self, data):
        data = super(TravelFilterBoxSerializer, self).to_internal_value(data)

        # Adjust month because frontend sends 0-11
        if 'month' in data:
            data['month'] += 1

        # Mode of travel is an array field and the lookup has to be a list
        if 'mode_of_travel__contains' in data:
            data['mode_of_travel__contains'] = [data['mode_of_travel__contains']]

        return data
