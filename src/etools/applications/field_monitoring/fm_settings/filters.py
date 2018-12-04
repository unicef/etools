from datetime import date

from rest_framework.filters import BaseFilterBackend


class CPOutputIsActiveFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        filter_value = request.query_params.get('is_active')
        if filter_value is None:
            return queryset

        if filter_value.lower() == 'true':
            return queryset.filter(to_date__gte=date.today())
        else:
            return queryset.filter(to_date__lt=date.today())
