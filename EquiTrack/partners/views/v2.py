import operator
import functools

from django.shortcuts import get_object_or_404
from django.http import HttpResponse, StreamingHttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.settings import api_settings
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





class PartnerInterventionListAPIView(ListAPIView):
    queryset = Intervention.objects.all()
    serializer_class = InterventionSerializer
    permission_classes = (PartnerPermission,)

    def list(self, request, pk=None, format=None):
        """
        Return All Interventions for Partner
        """
        interventions = Intervention.objects.filter(partner_id=pk)
        serializer = InterventionSerializer(interventions, many=True)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class AgreementInterventionsListAPIView(ListAPIView):
    serializer_class = InterventionSerializer
    filter_backends = (PartnerScopeFilter,)
    permission_classes = (PartneshipManagerPermission,)

    def list(self, request, partner_pk=None, pk=None, format=None):
        """
        Return All Interventions for Partner and Agreement
        """
        if partner_pk:
            interventions = PCA.objects.filter(partner_id=partner_pk, agreement_id=pk)
        else:
            interventions = PCA.objects.filter(agreement_id=pk)
        serializer = InterventionSerializer(interventions, many=True)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )




class PartnerStaffMemberListAPIVIew(ListCreateAPIView):
    """
    Returns a list of all Partner staff members
    """
    queryset = PartnerStaffMember.objects.all()
    serializer_class = PartnerStaffMemberDetailSerializer
    permission_classes = (PartneshipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)

    def get_serializer_class(self, format=None):
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") == 'csv':
                    return PartnerStaffMemberExportSerializer
        if self.request.method == "POST":
            return PartnerStaffMemberCreateUpdateSerializer
        return super(PartnerStaffMemberListAPIVIew, self).get_serializer_class()

    def list(self, request, partner_pk=None, format=None):
        """
            Checks for format query parameter
            :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super(PartnerStaffMemberListAPIVIew, self).list(request)
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                response['Content-Disposition'] = "attachment;filename=staff-members.csv"
        return response


class PartnerStaffMemberDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = PartnerStaffMember.objects.all()
    serializer_class = PartnerStaffMemberDetailSerializer
    permission_classes = (PartneshipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)

    def get_serializer_class(self, format=None):
        if self.request.method in ["PUT", "PATCH"]:
            return PartnerStaffMemberCreateUpdateSerializer
        return super(PartnerStaffMemberDetailAPIView, self).get_serializer_class()


class PartnerStaffMemberPropertiesAPIView(RetrieveAPIView):
    """
    Gets the details of Staff Member that belongs to a partner
    """
    serializer_class = PartnerStaffMemberPropertiesSerializer
    queryset = PartnerStaffMember.objects.all()
    permission_classes = (PartneshipManagerPermission,)

    def get_object(self):
        queryset = self.get_queryset()

        # Get the current partnerstaffmember
        try:
            current_member = PartnerStaffMember.objects.get(id=self.request.user.profile.partner_staff_member)
        except PartnerStaffMember.DoesNotExist:
            raise Exception('there is no PartnerStaffMember record associated with this user')

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        # If current member is actually looking for themselves return right away.
        if self.kwargs[lookup_url_kwarg] == str(current_member.id):
            return current_member

        filter = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        # allow lookup only for PSMs inside the same partnership
        filter['partner'] = current_member.partner

        obj = get_object_or_404(queryset, **filter)
        self.check_object_permissions(self.request, obj)
        return obj
