from __future__ import unicode_literals

from rest_framework.filters import BaseFilterBackend


class TravelRelatedModelFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        # This should be attached only to viewsets which gets travel_pk
        return queryset.filter(travel__pk=view.kwargs['travel_pk'])
