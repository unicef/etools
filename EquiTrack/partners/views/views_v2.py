import operator
import functools

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from partners.models import Agreement, PCA
from partners.serializers.serializers import InterventionSerializer
from partners.serializers.serializers_v2 import AgreementListSerializer, AgreementSerializer
from partners.permissions import PartnerManagerPermission
from partners.filters import PartnerScopeFilter


class AgreementListAPIView(ListCreateAPIView):
    """
    Create new Agreements.
    Returns a list of Agreements.
    Returns related Interventions.
    """
    queryset = Agreement.objects.all()
    serializer_class = AgreementSerializer
    permission_classes = (PartnerManagerPermission,)
    filter_backends = (PartnerScopeFilter,)

    def get_serializer_class(self):
        """
        Use restriceted field set for listing
        """
        if self.request.method == "GET":
            return AgreementListSerializer
        else:
            return super(AgreementListAPIView, self).get_serializer_class()

    def create(self, request, *args, **kwargs):
        """
        Add a new Agreement
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

            expression = functools.reduce(operator.and_, queries)
            return q.filter(expression)
        else:
            return q.all()


class AgreementInterventionsListAPIView(ListAPIView):
    queryset = PCA.objects.all()
    serializer_class = InterventionSerializer
    permission_classes = (PartnerManagerPermission,)
    filter_backends = (PartnerScopeFilter,)

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
    serializer_class = AgreementSerializer
    permission_classes = (PartnerManagerPermission,)

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
