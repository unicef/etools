from django.utils.translation import ugettext as _
from django.db.models import Q
from rest_framework import (
    permissions,
    status
)
from rest_framework.views import APIView
from rest_framework.response import Response

from funds.models import FundsReservationHeader, FundsReservationItem, Grant
from funds.serializers import FRsSerializer


class FRsView(APIView):
    """
    Returns the FRs requested with the values query param
    """
    permission_classes = (permissions.IsAdminUser,)

    def filter_by_donors(self, qs, donors):
        grant_numbers = Grant.objects.values_list(
            "name",
            flat=True
        ).filter(donor__pk__in=donors)
        qs = self.filter_by_grants(qs, None, list(grant_numbers))
        return qs

    def filter_by_grants(self, qs, grants, grant_numbers=[]):
        """Filter queryset by grant ids provided

        `name` field in Grants table matches `grant_number` in
        FundsReservationItem, from FundsReservationItem we can
        access FundsReservationHeader
        """
        if not isinstance(grant_numbers, list):
            return qs.none()

        if grants:
            grant_qs = Grant.objects.values_list(
                "name",
                flat=True
            ).filter(pk__in=grants)
            if grant_numbers:
                grant_qs = grant_qs.filter(name__in=grant_numbers)
            grant_numbers = grant_qs

        if not grant_numbers:
            qs = qs.none()
        else:
            fr_headers = FundsReservationItem.objects.values_list(
                "fund_reservation__pk",
                flat=True
            ).filter(grant_number__in=grant_numbers)
            qs = qs.filter(pk__in=fr_headers)
        return qs

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

        donors = [x for x in request.query_params.get("donors", "").split(",") if x]
        if donors:
            qs = self.filter_by_donors(qs, donors)

        grants = [x for x in request.query_params.get("grants", "").split(",") if x]
        if grants:
            qs = self.filter_by_grants(qs, grants)

        if not grants and not donors and qs.count() != len(values):
            return Response(
                data={'error': _('One or more of the FRs are used by another PD/SSFA '
                                 'or could not be found in eTools.')},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = FRsSerializer(qs)

        return Response(serializer.data)
