from datetime import date

from django.db import connection
from django.db.models import Q
from django.db.models.functions import TruncYear

from django_filters import rest_framework as filters
from rest_framework.filters import BaseFilterBackend

from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.utils.filters import M2MInFilter
from etools.applications.partners.models import Intervention
from etools.applications.reports.models import Result
from etools.applications.users.mixins import TPM_ACTIVE_GROUPS


class MonitoringActivitiesFilterSet(filters.FilterSet):
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
            'team_members': ['in'],
            'visit_lead': ['exact', 'in'],
            'location': ['exact', 'in'],
            'location_site': ['exact', 'in'],
            'partners': ['in'],
            'interventions': ['in'],
            'cp_outputs': ['in'],
            'start_date': ['gte', 'lte'],
            'end_date': ['gte', 'lte'],
            'status': ['exact', 'in'],
            'offices': ['exact', 'in'],
            'sections': ['in'],
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
            return queryset.filter(tpm_partner__isnull=False).distinct()
        else:
            return queryset.filter(is_staff=True)


class UserTPMPartnerFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        value = request.query_params.get('tpm_partner')
        if not value:
            return queryset

        return queryset.filter(
            realms__country=connection.tenant,
            realms__organization__tpmpartner=value,
            realms__group__name__in=TPM_ACTIVE_GROUPS,
        ).distinct()


class UserNameFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        with_name = request.query_params.get('with_name', '').lower()
        if with_name != 'true':
            return queryset

        return queryset.filter(
            Q(first_name__isnull=False, first_name__gt='') |
            Q(last_name__isnull=False, last_name__gt='')
        )


class CPOutputsFilterSet(filters.FilterSet):
    partners__in = filters.BaseInFilter(
        field_name='intervention_links__intervention__agreement__partner', distinct=True
    )
    active = filters.BooleanFilter(method='active_filter')

    class Meta:
        model = Result
        fields = ['partners__in', 'active']

    def active_filter(self, queryset, name, value):
        if value:
            return queryset.filter(to_date__gte=date.today())
        return queryset


class InterventionsFilterSet(filters.FilterSet):
    partners__in = filters.BaseInFilter(field_name='agreement__partner')
    cp_outputs__in = filters.BaseInFilter(field_name='result_links__cp_output', distinct=True)
    status__in = filters.BaseInFilter(field_name='status')

    class Meta:
        model = Intervention
        fields = ['partners__in', 'cp_outputs__in', 'status']


class HactForPartnerFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        hact_for_partner = request.query_params.get('hact_for_partner', '')
        if not hact_for_partner:
            return queryset

        return queryset.filter_hact_for_partner(hact_for_partner)
