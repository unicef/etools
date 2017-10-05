from django.utils.translation import ugettext as _
from django.db.models import Q
from rest_framework import (
    permissions,
    status
)
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import FundsReservationHeader
from .serializers import FRsSerializer


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
