import operator
import functools

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework_csv import renderers as r
from rest_framework.generics import (
    ListAPIView,
    CreateAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)

from partners.models import Agreement, PCA, PartnerStaffMember
from partners.serializers.v1 import InterventionSerializer
from partners.serializers.v2 import (
    AgreementListSerializer,
    AgreementExportSerializer,
    AgreementCreateUpdateSerializer,
    AgreementRetrieveSerializer,
    PartnerStaffMemberCreateSerializer,
    PartnerStaffMemberUpdateSerializer,
    PartnerStaffMemberDetailSerializer,
    PartnerStaffMemberPropertiesSerializer,
)
from partners.permissions import PartnerPermission, PartneshipManagerPermission
from partners.filters import PartnerScopeFilter


class AgreementListAPIView(ListCreateAPIView):
    """
    Create new Agreements.
    Returns a list of Agreements.
    """
    serializer_class = AgreementListSerializer
    filter_backends = (PartnerScopeFilter,)
    permission_classes = (PartneshipManagerPermission,)
    renderer_classes = (r.JSONRenderer, r.CSVRenderer)

    def get_serializer_class(self):
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

    def get_queryset(self):
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

    def list(self, request, partner_pk=None):
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


class AgreementInterventionsListAPIView(ListAPIView):
    serializer_class = InterventionSerializer
    filter_backends = (PartnerScopeFilter,)
    permission_classes = (PartneshipManagerPermission,)

    def list(self, request, partner_pk=None, pk=None):
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


class AgreementDetailAPIView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update Agreement.
    """
    queryset = Agreement.objects.all()
    serializer_class = AgreementRetrieveSerializer
    permission_classes = (PartneshipManagerPermission,)

    def get_serializer_class(self):
        """
        Use restriceted field set for listing
        """
        if self.request.method == "GET":
            return AgreementRetrieveSerializer
        elif self.request.method in ["POST", "PUT", "PATCH"]:
            return AgreementCreateUpdateSerializer
        return super(AgreementDetailAPIView, self).get_serializer_class()

    def retrieve(self, request, pk=None):
        """
        Returns an Agreement object for this Agreement PK
        """
        try:
            queryset = self.queryset.get(id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except Agreement.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class PartnerStaffMemberListAPIVIew(ListCreateAPIView):
    """
    Returns a list of all Partner staff members
    """
    queryset = PartnerStaffMember.objects.all()
    serializer_class = PartnerStaffMemberDetailSerializer
    permission_classes = (PartnerPermission,)
    filter_backends = (PartnerScopeFilter,)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PartnerStaffMemberCreateSerializer
        return super(PartnerStaffMemberListAPIVIew, self).get_serializer_class()


class PartnerStaffMemberDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = PartnerStaffMember.objects.all()
    serializer_class = PartnerStaffMemberDetailSerializer
    permission_classes = (PartnerPermission,)
    filter_backends = (PartnerScopeFilter,)

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return PartnerStaffMemberUpdateSerializer
        return super(PartnerStaffMemberDetailAPIView, self).get_serializer_class()


class PartnerStaffMemberPropertiesAPIView(RetrieveAPIView):
    """
    Gets the details of Staff Member that belongs to a partner
    """
    serializer_class = PartnerStaffMemberPropertiesSerializer
    queryset = PartnerStaffMember.objects.all()

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
