import functools
import operator

from django.db.models import Q

from rest_framework.generics import (
    ListAPIView)
from rest_framework.pagination import LimitOffsetPagination

from partners.filters import PartnerScopeFilter
from partners.models import (
    Intervention,
)
from partners.serializers.prp_v1 import PRPInterventionListSerializer
from partners.permissions import ListCreateAPIMixedPermission
from partners.views.helpers import set_tenant_or_fail


class PRPInterventionPagination(LimitOffsetPagination):
    default_limit = 100


class PRPInterventionListAPIView(ListAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = PRPInterventionListSerializer
    permission_classes = (ListCreateAPIMixedPermission, )
    filter_backends = (PartnerScopeFilter,)
    pagination_class = PRPInterventionPagination

    def paginate_queryset(self, queryset):
        return super(PRPInterventionListAPIView, self).paginate_queryset(queryset)

    def get_queryset(self, format=None):
        q = Intervention.objects.prefetch_related(
            'result_links__cp_output',
            'result_links__ll_results',
            'result_links__ll_results__applied_indicators__indicator',
            'result_links__ll_results__applied_indicators__disaggregation',
            'result_links__ll_results__applied_indicators__locations',
            'reporting_periods',
            'planned_budget__currency',
            'frs',
            'partner_focal_points',
            'unicef_focal_points',
            'agreement__authorized_officers',
        )

        query_params = self.request.query_params
        workspace = query_params.get('workspace', None)
        set_tenant_or_fail(workspace)

        if query_params:
            queries = []
            if "country_programme" in query_params.keys():
                queries.append(Q(agreement__country_programme=query_params.get("country_programme")))
            if "section" in query_params.keys():
                queries.append(Q(sections__pk=query_params.get("section")))
            if "status" in query_params.keys():
                queries.append(Q(status=query_params.get("status")))
            if "partner" in query_params.keys():
                queries.append(Q(agreement__partner=query_params.get("partner")))
            if "updated_before" in query_params.keys():
                queries.append(Q(modified__lte=query_params.get("updated_before")))
            if "updated_after" in query_params.keys():
                queries.append(Q(modified__gte=query_params.get("updated_after")))
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression).distinct()

        return q
