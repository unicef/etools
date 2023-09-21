from django.contrib.auth import get_user_model
from django.db.models.functions import TruncYear

from django_filters import rest_framework as filters
from rest_framework.filters import BaseFilterBackend, OrderingFilter

from etools.applications.tpm.models import TPMActivity, TPMVisit


class ReferenceNumberOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get('ordering', '')
        if not ordering.lstrip('-') == 'reference_number':
            return queryset

        ordering_params = ['created_year', 'id']

        return queryset.annotate(created_year=TruncYear('created'))\
            .order_by(*map(lambda param: ('' if ordering == 'reference_number' else '-') + param, ordering_params))


class TPMVisitFilter(filters.FilterSet):
    tpm_activities__offices__in = filters.BaseInFilter(field_name="tpm_activities__offices")
    tpm_partner_focal_points__in = filters.BaseInFilter(field_name="tpm_partner_focal_points")

    class Meta:
        model = TPMVisit
        fields = {
            'tpm_partner': ['exact', 'in'],
            'tpm_activities__section': ['exact', 'in'],
            'tpm_activities__partner': ['exact', 'in'],
            'tpm_activities__locations': ['exact'],
            'tpm_activities__offices': ['exact', 'in'],
            'tpm_activities__cp_output': ['exact', 'in'],
            'tpm_activities__intervention': ['exact'],
            'tpm_activities__date': ['exact', 'lte', 'gte', 'gt', 'lt'],
            'status': ['exact', 'in'],
            'tpm_activities__unicef_focal_points': ['exact'],
            'tpm_partner_focal_points': ['exact', 'in'],
        }


class TPMActivityFilter(filters.FilterSet):
    offices__in = filters.BaseInFilter(field_name="offices")

    class Meta:
        model = TPMActivity
        fields = {
            'tpm_visit': ['exact'],
            'section': ['exact', 'in'],
            'offices': ['exact', 'in'],
            'tpm_visit__tpm_partner': ['exact'],
            'partner': ['exact', 'in'],
            'tpm_visit__status': ['exact', 'in'],
            'is_pv': ['exact', ],
            'date': ['exact', 'year'],
            'intervention': ['exact', 'in'],
        }


class TPMStaffMembersFilterSet(filters.FilterSet):
    user__is_active = filters.BooleanFilter(field_name='is_active')

    class Meta:
        model = get_user_model()
        fields = {}


class StaffMembersOrderingFilter(OrderingFilter):
    """
    backwards compatible staff members ordering: since we're using user instead of extra model, `user__` is not needed
    """

    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        if not ordering:
            return ordering
        return [param.replace('user__', '') for param in ordering]
