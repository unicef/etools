import operator
import functools

from django.db.models import Q
from django.http import HttpResponse
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from partners.models import GovernmentIntervention
from partners.serializers.v2 import (
    GovernmentInterventionListSerializer,
    GovernmentInterventionCreateUpdateSerializer,
    GovernmentInterventionDetailSerializer,
)
from partners.exports import GovernmentExport
from partners.filters import GovernmentInterventionExportFilter, PartnerScopeFilter
from partners.permissions import PartnerPermission


class GovernmentInterventionExportAPIView(ListAPIView):
    queryset = GovernmentIntervention.objects.all()
    serializer_class = GovernmentInterventionDetailSerializer
    permission_classes = (PartnerPermission,)
    filter_backends = (PartnerScopeFilter, GovernmentInterventionExportFilter,)

    def list(self, request, partner_pk=None):
        queryset = self.get_queryset()
        queryset = self.filter_queryset(queryset)
        dataset = GovernmentExport().export(queryset)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ModelExportGovernmentInterventions.csv"'
        response.write(dataset.csv)
        return response


class GovernmentInterventionListAPIView(ListCreateAPIView):
    serializer_class = GovernmentInterventionListSerializer
    permission_classes = (PartnerPermission,)

    def get_serializer_class(self, format=None):
        """
        Use restriceted field set for listing
        """
        if self.request.method == "POST":
            return GovernmentInterventionCreateUpdateSerializer
        return super(GovernmentInterventionListAPIView, self).get_serializer_class()

    def get_queryset(self):
        q = GovernmentIntervention.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []

            if "partner_name" in query_params.keys():
                queries.append(Q(partner__name=query_params.get("partner_name")))
            if "result" in query_params.keys():
                queries.append(Q(results__result__in=[query_params.get("result")]))
            if "sector" in query_params.keys():
                queries.append(Q(results__sector__in=[query_params.get("sector")]))
            if "unicef_manager" in query_params.keys():
                queries.append(Q(results__unicef_managers__id=query_params.get("unicef_manager")))
            if "year" in query_params.keys():
                queries.append(Q(results__year__in=[query_params.get("year")]))
            if "search" in query_params.keys():
                queries.append(
                    Q(partner__name__icontains=query_params.get("search")) |
                    Q(number__icontains=query_params.get("search"))
                )

            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)
            else:
                q = q.all()
        return q


class GovernmentInterventionDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = GovernmentIntervention.objects.all()
    serializer_class = GovernmentInterventionDetailSerializer
    permission_classes = (PartnerPermission,)

    def get_serializer_class(self, format=None):
        if self.request.method in ["PUT", "PATCH"]:
            return GovernmentInterventionCreateUpdateSerializer
        else:
            return super(GovernmentInterventionDetailAPIView, self).get_serializer_class()
