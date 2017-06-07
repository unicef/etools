from __future__ import unicode_literals

import calendar
from datetime import date

from django.db.models.query_utils import Q
from rest_framework.filters import BaseFilterBackend

from partners.models import InterventionResultLink
from t2f.filters import BaseSearchFilter, BaseSortFilter, BaseFilterBoxFilter
from t2f.models import Travel
from t2f.serializers.filters.travel_list import ShowHiddenFilterSerializer, TravelFilterBoxSerializer,\
    TravelSortFilterSerializer


class TravelSearchFilter(BaseSearchFilter):
    _search_fields = ('id', 'reference_number', 'traveler__first_name', 'traveler__last_name', 'purpose',
                      'section__name', 'office__name', 'supervisor__first_name', 'supervisor__last_name')


class TravelSortFilter(BaseSortFilter):
    serializer_class = TravelSortFilterSerializer

    def compose_sort_key(self, sort_by, reverse):
        if sort_by == 'traveler__get_full_name':
            first_name_lookup = super(TravelSortFilter, self).compose_sort_key('traveler__first_name', reverse)
            last_name_lookup = super(TravelSortFilter, self).compose_sort_key('traveler__last_name', reverse)
        elif sort_by == 'supervisor__get_full_name':
            first_name_lookup = super(TravelSortFilter, self).compose_sort_key('supervisor__first_name', reverse)
            last_name_lookup = super(TravelSortFilter, self).compose_sort_key('supervisor__last_name', reverse)
        else:
            return super(TravelSortFilter, self).compose_sort_key(sort_by, reverse)
        return first_name_lookup, last_name_lookup


class TravelFilterBoxFilter(BaseFilterBoxFilter):
    serializer_class = TravelFilterBoxSerializer

    def _get_filter_kwargs(self, request, queryset, view):
        data = super(TravelFilterBoxFilter, self)._get_filter_kwargs(request, queryset, view)

        # Construct a backend readable date
        travel_type = data.pop('travel_type', None)
        if travel_type:
            data['activities__travel_type'] = travel_type

        year = data.pop('year', None)
        month = data.pop('month', None)
        if year:
            if month:
                start_date = date(year, month, 1)
                last_day_of_month = calendar.monthrange(year, month)[1]
                end_date = date(year, month, last_day_of_month)
            else:
                start_date = date(year, 1, 1)
                end_date = date(year, 12, 31)

            data['start_date__lte'] = end_date
            data['end_date__gte'] = start_date
        else:
            if month:
                data['start_date__month__lte'] = month
                data['end_date__month__gte'] = month

        cp_output = data.pop('cp_output', None)
        if cp_output:
            data['activities__result_id'] = cp_output

        return data


class ShowHiddenFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        serializer = ShowHiddenFilterSerializer(data=request.GET)
        if not serializer.is_valid():
            return queryset
        data = serializer.validated_data

        show_hidden = data['show_hidden']
        if not show_hidden:
            q = Q(hidden=True) | Q(status=Travel.CANCELLED)
            queryset = queryset.exclude(q)

        return queryset
