
import datetime

from django.utils.translation import ugettext as _
from django.db.models import Q
from rest_framework import (
    viewsets,
    mixins,
    permissions,
    status
)
from rest_framework.views import APIView
from rest_framework.decorators import detail_route
from rest_framework.response import Response

from .models import Donor, Grant, FundsReservationHeader
from .serializers import (
    DonorSerializer,
    GrantSerializer,
    FRsSerializer
)


class DonorViewSet(mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    """
    Returns a list of all Donors
    """
    queryset = Donor.objects.all()
    serializer_class = DonorSerializer
    permission_classes = (permissions.IsAdminUser,)

    @detail_route(methods=['get'], url_path='grants')
    def grants(self, request, pk=None):
        """
        Return all the Grants for this Donor
        """
        data = Grant.objects.filter(donor_id=pk).values()
        return Response(
            data,
            status=status.HTTP_200_OK,
        )


class GrantViewSet(mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    """
    Returns a list of all Grants
    """
    queryset = Grant.objects.all()
    serializer_class = GrantSerializer
    permission_classes = (permissions.IsAdminUser,)



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


        today = datetime.datetime.utcnow().date()
        qs = FundsReservationHeader.objects.filter(end_date__gte=today, fr_number__in=values)

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

