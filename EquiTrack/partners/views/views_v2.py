import operator
import functools

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework_csv import renderers as r
from rest_framework.generics import (
    ListCreateAPIView,
    ListAPIView,
    RetrieveUpdateDestroyAPIView,
)
from django.http import HttpResponse, StreamingHttpResponse

from partners.models import PartnerOrganization, PCA
from partners.permissions import PartnerPermission
from partners.serializers.serializers import PartnerOrganizationSerializer, InterventionSerializer
from partners.serializers.serializers_v2 import PartnerOrganizationExportSerializer
from partners.filters import PartnerScopeFilter


class PartnerOrganizationListAPIView(ListCreateAPIView):
    """
    Create new Partners.
    Returns a list of Partners.
    """
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationSerializer
    permission_classes = (PartnerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (r.JSONRenderer, r.CSVRenderer)

    def get_serializer_class(self):
        """
        Use restriceted field set for listing
        """
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") == 'csv':
                    return PartnerOrganizationExportSerializer
            return PartnerOrganizationSerializer
        else:
            return super(PartnerOrganizationListAPIView, self).get_serializer_class()

    def create(self, request, *args, **kwargs):
        """
        Add a new Partner
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.instance = serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def get_queryset(self, format=None):
        q = PartnerOrganization.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []

            if "partner_type" in query_params.keys():
                queries.append(Q(partner_type=query_params.get("partner_type")))
            if "cso_type" in query_params.keys():
                queries.append(Q(cso_type=query_params.get("cso_type")))
            if "hidden" in query_params.keys():
                queries.append(Q(hidden=query_params.get("hidden")))
            if "search" in query_params.keys():
                queries.append(
                    Q(name__icontains=query_params.get("search")) |
                    Q(vendor_number__icontains=query_params.get("search")) |
                    Q(short_name__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)
        return q

    def list(self, request):
        """
        Checks for format query parameter
        :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super(PartnerOrganizationListAPIView, self).list(request)
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                response['Content-Disposition'] = "attachment;filename=partner.csv"

        return response



class PartnerOrganizationDetailAPIView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update Agreement.
    """
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationSerializer
    permission_classes = (PartnerPermission,)

    def retrieve(self, request, pk=None, format=None):
        """
        Returns an Partner object for this partner PK
        """
        try:
            queryset = self.queryset.get(id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except PartnerOrganization.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class PartnerInterventionListAPIView(ListAPIView):
    queryset = PCA.objects.all()
    serializer_class = InterventionSerializer
    permission_classes = (PartnerPermission,)

    def list(self, request, pk=None, format=None):
        """
        Return All Interventions for Partner
        """
        interventions = PCA.objects.filter(partner_id=pk)
        serializer = InterventionSerializer(interventions, many=True)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
