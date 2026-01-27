from django_filters import rest_framework as filters

from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.utils.filters import M2MInFilter


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
