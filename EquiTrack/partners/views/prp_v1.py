import functools

import operator
from django.db.models import Q, connection
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListAPIView)

from partners.filters import PartnerScopeFilter
from partners.models import (
    Intervention,
)
from partners.serializers.prp_v1 import PRPInterventionListSerializer
from partners.permissions import ListCreateAPIMixedPermission
from users.models import Country as Workspace


class PRPInterventionListAPIView(ListAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = PRPInterventionListSerializer
    permission_classes = (ListCreateAPIMixedPermission, )
    filter_backends = (PartnerScopeFilter,)


    def get_queryset(self, format=None):
        q = Intervention.objects.prefetch_related(
            'result_links__cp_output',
            'result_links__ll_results',
            'result_links__ll_results__applied_indicators__indicator',
            'result_links__ll_results__applied_indicators__disaggregation',
            'result_links__ll_results__applied_indicators__locations',
            'frs',
            'partner_focal_points',
            'unicef_focal_points',
            'agreement__authorized_officers',
        )

        query_params = self.request.query_params
        workspace = query_params.get('workspace', None)
        if workspace is None:
            raise ValidationError('Workspace is required as a queryparam')
        else:
            try:
                ws = Workspace.objects.get(business_area_code=workspace)
            except Workspace.DoesNotExist:
                raise ValidationError('Workspace code provided is not a valid business_area_code: %s' % workspace)
            else:
                connection.set_tenant(ws)

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
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression).distinct()

        return q

    def list(self, request):
        # todo: customize this (or remove if no customizations needed)
        return super(PRPInterventionListAPIView, self).list(request)
