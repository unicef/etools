from rest_framework.filters import BaseFilterBackend


class TaskSectionsFilter(BaseFilterBackend):
    """
    Filter for filtering by flattened list instead of classic complex schema
    sections__in=1,2,3 instead of sections=1&sections=2&sections=3
    """
    def filter_queryset(self, request, queryset, view):
        value = request.query_params.get('sections__in')
        if not value:
            return queryset

        return queryset.filter(sections__in=value.split(','))
