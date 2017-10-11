import operator
import functools

from django.utils.translation import ugettext as _
from django.db.models import Q
from rest_framework import (
    permissions,
    status
)
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_csv import renderers as r

from funds.models import (
    FundsCommitmentHeader,
    FundsReservationHeader,
    FundsReservationItem,
)
from funds.renderers import (
    FundsCommitmentHeaderCsvFlatRenderer,
    FundsCommitmentHeaderCsvRenderer,
    FundsReservationHeaderCsvRenderer,
    FundsReservationHeaderCsvFlatRenderer,
    FundsReservationItemCsvFlatRenderer,
    FundsReservationItemCsvRenderer,
)
from funds.serializers import (
    FRHeaderSerializer,
    FRsSerializer,
    FundsCommitmentHeaderSerializer,
    FundsReservationHeaderExportFlatSerializer,
    FundsReservationHeaderExportSerializer,
    FundsReservationItemExportFlatSerializer,
    FundsReservationItemExportSerializer,
    FundsReservationItemSerializer,
)
from partners.filters import PartnerScopeFilter
from partners.permissions import PartneshipManagerPermission


class FRsView(APIView):
    """
    Returns the FRs requested with the values query param
    """
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request, format=None):
        values = request.query_params.get("values", '').split(",")
        intervention_id = request.query_params.get("intervention", None)

        if not values[0]:
            return Response(data={'error': _('Values are required')}, status=status.HTTP_400_BAD_REQUEST)

        qs = FundsReservationHeader.objects.filter(fr_number__in=values)

        if intervention_id:
            qs = qs.filter((Q(intervention__id=intervention_id) | Q(intervention__isnull=True)))
        else:
            qs = qs.filter(intervention__isnull=True)

        if qs.count() != len(values):
            return Response(
                data={'error': _('One or more of the FRs selected is either expired, '
                                 'has been used by another intervention or could not be found in eTools')},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = FRsSerializer(qs)

        return Response(serializer.data)


class FundsReservationHeaderListAPIView(ListAPIView):
    """
    Returns a list of FundsReservationHeaders.
    """
    serializer_class = FRHeaderSerializer
    permission_classes = (PartneshipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        r.JSONRenderer,
        FundsReservationHeaderCsvRenderer,
        FundsReservationHeaderCsvFlatRenderer,
    )

    def get_serializer_class(self):
        """
        Use different serilizers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return FundsReservationHeaderExportSerializer
            if query_params.get("format") == 'csv_flat':
                return FundsReservationHeaderExportFlatSerializer
        return super(FundsReservationHeaderListAPIView, self).get_serializer_class()

    def get_queryset(self, format=None):
        q = FundsReservationHeader.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(intervention__number__icontains=query_params.get("search")) |
                    Q(vendor_code__icontains=query_params.get("search")) |
                    Q(fr_number__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        return q


class FundsReservationItemListAPIView(ListAPIView):
    """
    Returns a list of FundsReservationItems.
    """
    serializer_class = FundsReservationItemSerializer
    permission_classes = (PartneshipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        r.JSONRenderer,
        FundsReservationItemCsvRenderer,
        FundsReservationItemCsvFlatRenderer,
    )

    def get_serializer_class(self):
        """
        Use different serilizers for methods
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return FundsReservationItemExportSerializer
            if query_params.get("format") == 'csv_flat':
                return FundsReservationItemExportFlatSerializer
        return super(FundsReservationItemListAPIView, self).get_serializer_class()

    def get_queryset(self, format=None):
        q = FundsReservationItem.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(fund_reservation__intervention__number__icontains=query_params.get("search")) |
                    Q(fund_reservation__fr_number__icontains=query_params.get("search")) |
                    Q(fund_reservation__fr_ref_number__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        return q


class FundsCommitmentHeaderListAPIView(ListAPIView):
    """
    Returns a list of FundsCommitmentHeaders.
    """
    serializer_class = FundsCommitmentHeaderSerializer
    permission_classes = (PartneshipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (
        r.JSONRenderer,
        FundsCommitmentHeaderCsvRenderer,
        FundsCommitmentHeaderCsvFlatRenderer,
    )

    def get_queryset(self, format=None):
        q = FundsCommitmentHeader.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []
            if "search" in query_params.keys():
                queries.append(
                    Q(vendor_code__icontains=query_params.get("search")) |
                    Q(fc_number__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)

        return q
