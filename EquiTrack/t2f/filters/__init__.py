from __future__ import unicode_literals

from django.db.models.query_utils import Q
from rest_framework.filters import BaseFilterBackend

from t2f.serializers.filters import SearchFilterSerializer


class TravelRelatedModelFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # This should be attached only to viewsets which gets travel_pk
        return queryset.filter(travel__pk=view.kwargs['travel_pk'])


class BaseSearchFilter(BaseFilterBackend):
    _search_fields = ()

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


class BaseSortFilter(BaseFilterBackend):
    serializer_class = None

    def filter_queryset(self, request, queryset, view):
        serializer = self.serializer_class(data=request.GET)
        if not serializer.is_valid():
            return queryset
        data = serializer.validated_data

        prefix = '-' if data['reverse'] else ''
        sort_by = '{}{}'.format(prefix, data['sort_by'])
        return queryset.order_by(sort_by)


class BaseFilterBoxFilter(BaseFilterBackend):
    """
    Does the filtering based on the filter parameters coming from the frontend
    """
    serializer_class = None

    def filter_queryset(self, request, queryset, view):
        data = self._get_filter_kwargs(request, queryset, view)
        # To have proper keys in data dict, the serializer renames the incoming values according to the needs
        return queryset.filter(**data)

    def _get_filter_kwargs(self, request, queryset, view):
        serializer = self.serializer_class(data=request.GET)
        if not serializer.is_valid():
            return queryset
        return serializer.validated_data
