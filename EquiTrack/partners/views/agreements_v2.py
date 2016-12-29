import operator
import functools

from django.shortcuts import get_object_or_404
from django.http import HttpResponse, StreamingHttpResponse
from rest_framework import status

from django.db import transaction
from django.db.models import Q
from rest_framework.response import Response

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.settings import api_settings
from rest_framework_csv import renderers as r
from rest_framework.generics import (
    ListCreateAPIView,
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)

from partners.models import (
    Agreement,
    AgreementAmendment,
)
from partners.serializers.v1 import InterventionSerializer
from partners.serializers.agreements_v2 import (
    AgreementListSerializer,
    AgreementExportSerializer,
    AgreementCreateUpdateSerializer,
    AgreementRetrieveSerializer,
    AgreementAmendmentCreateUpdateSerializer
)
from partners.serializers.partner_organization_v2 import (

    PartnerStaffMemberDetailSerializer,
    PartnerStaffMemberPropertiesSerializer,
    PartnerStaffMemberExportSerializer,
    PartnerOrganizationExportSerializer,
    PartnerOrganizationListSerializer,
    PartnerOrganizationDetailSerializer,
    PartnerOrganizationCreateUpdateSerializer,
    PartnerStaffMemberCreateUpdateSerializer,
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



class AgreementListAPIView(ListCreateAPIView):
    """
    Create new Agreements.
    Returns a list of Agreements.
    """
    serializer_class = AgreementListSerializer
    filter_backends = (PartnerScopeFilter,)
    permission_classes = (IsAdminUser,)
    renderer_classes = (r.JSONRenderer, r.CSVRenderer)

    def get_serializer_class(self, format=None):
        """
        Use restriceted field set for listing
        """
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") == 'csv':
                    return AgreementExportSerializer
            return AgreementListSerializer
        elif self.request.method == "POST":
            return AgreementCreateUpdateSerializer
        return super(AgreementListAPIView, self).get_serializer_class()

    def get_queryset(self, format=None):
        q = Agreement.view_objects
        query_params = self.request.query_params

        if query_params:
            queries = []

            if "agreement_type" in query_params.keys():
                queries.append(Q(agreement_type=query_params.get("agreement_type")))
            if "status" in query_params.keys():
                queries.append(Q(status=query_params.get("status")))
            if "partner_name" in query_params.keys():
                queries.append(Q(partner__name=query_params.get("partner_name")))
            if "start" in query_params.keys():
                queries.append(Q(start__gt=query_params.get("start")))
            if "end" in query_params.keys():
                queries.append(Q(end__lte=query_params.get("end")))
            if "search" in query_params.keys():
                queries.append(
                    Q(partner__name__icontains=query_params.get("search")) |
                    Q(agreement_number__icontains=query_params.get("search"))
                )

            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)
            else:
                q = q.all()
        return q

    def list(self, request, partner_pk=None, format=None):
        """
            Checks for format query parameter
            :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super(AgreementListAPIView, self).list(request)
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                response['Content-Disposition'] = "attachment;filename=agreements.csv"

        return response

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serialier = self.get_serializer(data=request.data)
        serialier.is_valid(raise_exception=True)
        agreement = serialier.save()

        headers = self.get_success_headers(serialier.data)
        return Response(serialier.data, status=status.HTTP_201_CREATED, headers=headers)

class AgreementDetailAPIView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update Agreement.
    """
    queryset = Agreement.objects.all()
    serializer_class = AgreementRetrieveSerializer
    permission_classes = (IsAdminUser,)

    def get_serializer_class(self, format=None):
        """
        Use restriceted field set for listing
        """
        if self.request.method == "GET":
            return AgreementRetrieveSerializer
        elif self.request.method in ["PATCH"]:
            return AgreementCreateUpdateSerializer
        return super(AgreementDetailAPIView, self).get_serializer_class()

    def update(self, request, *args, **kwargs):

        partial = kwargs.pop('partial', False)
        amendments = request.data.pop('amendments', None)

        instance = self.get_object()
        agreement_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        agreement_serializer.is_valid(raise_exception=True)
        agreement = agreement_serializer.save()

        if amendments:
            for item in amendments:
                item.update({u"agreement": agreement.pk})
                if item.get('id', None):
                    try:
                        amd_instance = AgreementAmendment.objects.get(id=item['id'])
                    except AgreementAmendment.DoesNotExist:
                        amd_instance = None

                    amd_serializer = AgreementAmendmentCreateUpdateSerializer(instance=amd_instance,
                                                                                       data=item,
                                                                                       partial=partial)
                else:
                    amd_serializer = AgreementAmendmentCreateUpdateSerializer(data=item)

                try:
                    amd_serializer.is_valid(raise_exception=True)
                except ValidationError as e:
                    e.detail = {'amendments': e.detail}
                    raise e

                amd_serializer.save()

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()
            amd_serializer = self.get_serializer(instance)

        return Response(agreement_serializer.data)

