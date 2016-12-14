from __future__ import unicode_literals

import calendar
from datetime import date

from django.db.models.query_utils import Q
from rest_framework.filters import BaseFilterBackend

from et2f.models import Travel
from et2f.serializers.filters import SearchFilterSerializer, ShowHiddenFilterSerializer, SortFilterSerializer, \
    FilterBoxFilterSerializer


class SearchFilter(BaseFilterBackend):
    _search_fields = ('id', 'reference_number', 'traveler__first_name', 'traveler__last_name', 'purpose',
                      'section__name', 'office__name', 'supervisor__first_name', 'supervisor__last_name')

    def filter_queryset(self, request, queryset, view):
        serializer = SearchFilterSerializer(data=request.GET)
        if not serializer.is_valid():
            return queryset
        data = serializer.validated_data

        search_str = data['search']
        if search_str:
            q = Q()
            for field_name in self._search_fields:
                constructed_field_name = '{}__iexact'.format(field_name)
                q |= Q(**{constructed_field_name: search_str})
            queryset = queryset.filter(q)

        return queryset


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


class SortFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        serializer = SortFilterSerializer(data=request.GET)
        if not serializer.is_valid():
            return queryset
        data = serializer.validated_data

        prefix = '-' if data['reverse'] else ''
        sort_by = '{}{}'.format(prefix, data['sort_by'])
        return queryset.order_by(sort_by)


class FilterBoxFilter(BaseFilterBackend):
    """
    Does the filtering based on the filter parameters coming from the frontend
    """
    def filter_queryset(self, request, queryset, view):
        serializer = FilterBoxFilterSerializer(data=request.GET)
        if not serializer.is_valid():
            return queryset
        data = serializer.validated_data

        # Construct a backend readable date
        year = data.pop('year', None)
        month = data.pop('month', None)
        if year:
            if month:
                start_date = date(year, month, 1)
                last_day_of_month = calendar.monthrange(year, month)[1]
                end_date = date(year, month, last_day_of_month)
            else:
                start_date = date(year, 1, 1)
                end_date = data(year, 12, 31)

            data['start_date__lte'] = end_date
            data['end_date__gte'] = start_date

        # TODO simon: figure out what to do with this
        data.pop('cp_output', None)

        return queryset.filter(**data)


class TravelAttachmentFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(travel__pk=view.kwargs['travel_pk'])
