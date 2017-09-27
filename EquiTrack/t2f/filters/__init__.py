from __future__ import unicode_literals

from django.db.models.query_utils import Q
from django.db.models import F
from rest_framework.filters import BaseFilterBackend

from t2f.serializers.filters import SearchFilterSerializer


class TravelRelatedModelFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # This should be attached only to viewsets which gets travel_pk
        return queryset.filter(travel__pk=view.kwargs['travel_pk'])


class TravelActivityPartnerFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset \
            .filter(partner__pk=view.kwargs['partner_organization_pk']) \
            .prefetch_related('travels') \
            .filter(travels__traveler=F("primary_traveler"))


class TravelActivityInterventionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        return queryset \
            .filter(partnership__pk=view.kwargs['partnership_pk']) \
            .prefetch_related('travels') \
            .filter(travels__traveler=F("primary_traveler"))


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
                constructed_field_name = '{}__icontains'.format(field_name)
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

        sort_by = self.compose_sort_key(data['sort_by'], data['reverse'])
        # This is to support multiple lookups for special cases
        if not isinstance(sort_by, (list, tuple)):
            sort_by = [sort_by]
        return queryset.order_by(*sort_by)

    def compose_sort_key(self, sort_by, reverse):
        prefix = '-' if reverse else ''
        return '{}{}'.format(prefix, sort_by)


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
