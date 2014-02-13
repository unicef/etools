__author__ = 'jcranwellward'

from django.core.cache import cache

from rest_framework.response import Response
from rest_framework.generics import ListAPIView

from .models import Sector
from .serializers import GWLocationSerializer
from reports.serializers import SectorSerializer
from reports.models import (
    Rrp5Output,
    Unit
)
from locations.models import (
    GatewayType
)
from partners.models import (
    PartnerOrganization,
    GwPCALocation,
    IndicatorProgress,
)


class SectorView(ListAPIView):

    model = Sector
    serializer_class = SectorSerializer


class IndicatorProgressView(ListAPIView):

    model = IndicatorProgress


class GatewayView(ListAPIView):

    model = GatewayType


class OutputViews(ListAPIView):

    model = Rrp5Output


class UnitView(ListAPIView):

    model = Unit


class PartnerView(ListAPIView):

    model = PartnerOrganization


class LocationView(ListAPIView):

    model = GwPCALocation
    serializer_class = GWLocationSerializer

    def get_queryset(self):
        """
        Return locations with GPS points only
        """
        return self.model.objects.filter(
            location__point__isnull=False
        )

    def list(self, request, *args, **kwargs):
        """
        Override parent and cache the location list
        unless new locations have been added
        """
        data = cache.get('locations')
        if not data or len(data) < self.get_queryset().count():
            response = super(LocationView, self).list(request, *args, **kwargs)
            cache.set('locations', response.data, 0)
            return response
        return Response(data)