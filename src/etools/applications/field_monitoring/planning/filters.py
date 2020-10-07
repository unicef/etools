from django.db.models.functions import TruncYear

from django_filters import rest_framework as filters
from rest_framework.filters import BaseFilterBackend

from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.utils.filters import M2MInFilter
from etools.applications.partners.models import Intervention
from etools.applications.reports.models import Result


class MonitoringActivitiesFilterSet(filters.FilterSet):
    team_members__in = M2MInFilter(field_name="team_members")
    partners__in = M2MInFilter(field_name="partners")
    interventions__in = M2MInFilter(field_name="interventions")
    cp_outputs__in = M2MInFilter(field_name="cp_outputs")

    class Meta:
        model = MonitoringActivity
        fields = {
            'monitor_type': ['exact'],
            'tpm_partner': ['exact', 'in'],
            'team_members': ['in'],
            'person_responsible': ['exact', 'in'],
            'location': ['exact', 'in'],
            'location_site': ['exact', 'in'],
            'partners': ['in'],
            'interventions': ['in'],
            'cp_outputs': ['in'],
            'start_date': ['gte', 'lte'],
            'end_date': ['gte', 'lte'],
            'status': ['exact', 'in'],
            'field_office': ['exact', 'in'],
        }


class ReferenceNumberOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get('ordering', '')
        if not ordering.lstrip('-') == 'reference_number':
            return queryset

        asc_desc = "-" if ordering.startswith("-") else ""
        ordering_params = ["{}{}".format(asc_desc, param) for param in ["created_year", "id"]]
        return queryset.annotate(created_year=TruncYear("created")).order_by(*ordering_params)


class UserTypeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        value = request.query_params.get('user_type')
        if not value:
            return queryset

        if value == 'tpm':
            return queryset.filter(tpmpartners_tpmpartnerstaffmember__isnull=False)
        else:
            return queryset.filter(is_staff=True)


class UserTPMPartnerFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        value = request.query_params.get('tpm_partner')
        if not value:
            return queryset

        return queryset.filter(
            tpmpartners_tpmpartnerstaffmember__tpm_partner=value
        )


class CPOutputsFilterSet(filters.FilterSet):
    partners__in = filters.BaseInFilter(
        field_name='intervention_links__intervention__agreement__partner', distinct=True
    )

    class Meta:
        model = Result
        fields = ['partners__in']


class InterventionsFilterSet(filters.FilterSet):
    partners__in = filters.BaseInFilter(field_name='agreement__partner')
    cp_outputs__in = filters.BaseInFilter(field_name='result_links__cp_output', distinct=True)

    class Meta:
        model = Intervention
        fields = ['partners__in', 'cp_outputs__in']
