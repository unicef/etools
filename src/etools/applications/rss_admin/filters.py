from django.contrib.admin.models import LogEntry

from django_filters import rest_framework as filters

from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.utils.filters import M2MInFilter


class LogEntryFilterSet(filters.FilterSet):
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = LogEntry
        fields = {
            'action_time': ['gte', 'lte'],
        }

    def filter_search(self, queryset, name, value):
        """Search across multiple text fields"""
        from django.db.models import Q
        return queryset.filter(
            Q(change_message__icontains=value) |
            Q(object_repr__icontains=value) |
            Q(user__first_name__icontains=value) |
            Q(user__last_name__icontains=value) |
            Q(user__email__icontains=value) |
            Q(user__username__icontains=value)
        )


class MonitoringActivityRssFilterSet(filters.FilterSet):
    team_members__in = M2MInFilter(field_name="team_members")
    partners__in = M2MInFilter(field_name="partners")
    interventions__in = M2MInFilter(field_name="interventions")
    cp_outputs__in = M2MInFilter(field_name="cp_outputs")
    sections__in = M2MInFilter(field_name="sections")
    offices__in = M2MInFilter(field_name="offices")

    class Meta:
        model = MonitoringActivity
        fields = {
            'monitor_type': ['exact'],
            'tpm_partner': ['exact', 'in'],
            'visit_lead': ['exact', 'in'],
            'location': ['exact', 'in'],
            'location_site': ['exact', 'in'],
            'start_date': ['gte', 'lte'],
            'end_date': ['gte', 'lte'],
            'status': ['exact', 'in'],
        }
