import functools
import operator

from django.db.models import Q

from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination

from etools.applications.partners.filters import PartnerScopeFilter
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.partners.permissions import ListCreateAPIMixedPermission
from etools.applications.partners.serializers.prp_v1 import (PRPInterventionListSerializer,
                                                             PRPPartnerOrganizationListSerializer,)
from etools.applications.partners.views.helpers import set_tenant_or_fail


class PRPInterventionPagination(LimitOffsetPagination):
    default_limit = 100


class PRPPartnerPagination(LimitOffsetPagination):
    default_limit = 300


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
            'result_links__ll_results__applied_indicators__disaggregation__disaggregation_values',
            'result_links__ll_results__applied_indicators__locations__gateway',
            'reporting_periods',
            'reporting_requirements',
            'frs',
            'partner_focal_points',
            'unicef_focal_points',
            'agreement__authorized_officers',
            'amendments',
            'flat_locations'
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


class PRPPartnerListAPIView(ListAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = PRPPartnerOrganizationListSerializer
    permission_classes = (ListCreateAPIMixedPermission, )
    pagination_class = PRPPartnerPagination

    def paginate_queryset(self, queryset):
        return super(PRPPartnerListAPIView, self).paginate_queryset(queryset)

    def get_queryset(self, format=None):
        q = PartnerOrganization.objects.all()

        query_params = self.request.query_params
        workspace = query_params.get('workspace', None)
        set_tenant_or_fail(workspace)

        return q
