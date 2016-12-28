import operator
import functools

from django.shortcuts import get_object_or_404
from django.http import HttpResponse, StreamingHttpResponse
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.permissions import IsAdminUser
from rest_framework_csv import renderers as r
from rest_framework.generics import (
    ListCreateAPIView,
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)

from partners.models import (
    PartnerOrganization,
    PCA,
    Agreement,
    PartnerStaffMember,
)
from partners.serializers.v1 import InterventionSerializer
from partners.serializers.agreements_v2 import (
    AgreementListSerializer,
    AgreementExportSerializer,
    AgreementCreateUpdateSerializer,
    AgreementRetrieveSerializer
)
from partners.serializers.partner_organization_v2 import (

    PartnerStaffMemberDetailSerializer,
    PartnerStaffMemberPropertiesSerializer,
    PartnerStaffMemberExportSerializer,
    PartnerOrganizationExportSerializer,
    PartnerOrganizationListSerializer,
    PartnerOrganizationDetailSerializer,
    PartnerOrganizationCreateUpdateSerializer,
    PartnerStaffMemberCreateSerializer,
    PartnerStaffMemberUpdateSerializer,
)
from partners.serializers.interventions_v2 import (
    InterventionListSerializer,
    InterventionDetailSerializer,
    InterventionCreateUpdateSerializer,
    InterventionExportSerializer

)
from partners.permissions import PartnerPermission, PartneshipManagerPermission
from partners.filters import PartnerScopeFilter

from django.http import HttpResponse, StreamingHttpResponse

from partners.models import PartnerOrganization, Intervention
from partners.permissions import PartnerPermission
from partners.serializers.v1 import PartnerOrganizationSerializer, InterventionSerializer

from partners.filters import PartnerScopeFilter


class PartnerOrganizationListAPIView(ListCreateAPIView):
    """
    Create new Partners.
    Returns a list of Partners.
    """
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationListSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (r.JSONRenderer, r.CSVRenderer)

    def get_serializer_class(self, format=None):
        """
        Use restriceted field set for listing
        """
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") == 'csv':
                    return PartnerOrganizationExportSerializer
        if self.request.method == "POST":
            return PartnerOrganizationCreateUpdateSerializer
        return super(PartnerOrganizationListAPIView, self).get_serializer_class()

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
                hidden = None
                if query_params.get("hidden").lower() == "true":
                    hidden = True
                if query_params.get("hidden").lower() == "false":
                    hidden = False
                if hidden != None:
                    queries.append(Q(hidden=hidden))
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

    def list(self, request, format=None):
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class PartnerOrganizationDetailAPIView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update PartnerOrganization.
    """
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationDetailSerializer
    permission_classes = (PartnerPermission,)

    def get_serializer_class(self, format=None):
        if self.request.method in ["PUT", "PATCH"]:
            return PartnerOrganizationCreateUpdateSerializer
        else:
            return super(PartnerOrganizationDetailAPIView, self).get_serializer_class()

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