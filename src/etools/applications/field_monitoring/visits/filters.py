from django.db.models.functions import TruncYear

from rest_framework.filters import BaseFilterBackend

from django_filters import rest_framework as filters

from etools.applications.field_monitoring.visits.models import Visit


class ReferenceNumberOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get('ordering', '')
        if not ordering.lstrip('-') == 'reference_number':
            return queryset

        ordering_params = ['created_year', 'id']

        return queryset.annotate(created_year=TruncYear('created'))\
            .order_by(*map(lambda param: ('' if ordering == 'reference_number' else '-') + param, ordering_params))


class VisitFilter(filters.FilterSet):
    class Meta:
        model = Visit
        fields = ({
            field: ['exact', 'in'] for field in [
                'location', 'location_site', 'status',
                'tasks__cp_output_config', 'tasks__partner',
            ]
        })


class VisitTeamMembersFilter(BaseFilterBackend):
    """
    Filter for using flattened list instead of classic complex schema
    team_members__in=1,2,3 instead of team_members=1&team_members=2&team_members=3
    """
    def filter_queryset(self, request, queryset, view):
        value = request.query_params.get('team_members__in')
        if not value:
            return queryset

        return queryset.filter(team_members__in=value.split(','))
