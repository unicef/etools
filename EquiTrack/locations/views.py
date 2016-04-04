__author__ = 'unicef-leb-inn'

from rest_framework import viewsets, mixins
from rest_framework.generics import ListAPIView

from .models import CartoDBTable, GatewayType, Location, Governorate, Region, Locality
from .serializers import (
    CartoDBTableSerializer,
    GatewayTypeSerializer,
    LocationSerializer,
    GovernorateSerializer,
    RegionSerializer,
    LocalitySerializer
)


class CartoDBTablesView(ListAPIView):
    """
    Gets a list of CartoDB tables for the mapping system
    """
    queryset = CartoDBTable.objects.all()
    serializer_class = CartoDBTableSerializer


class CartoDBTablesViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    """
    Gets a list of CartoDB tables for the mapping system
    """
    queryset = CartoDBTable.objects.all()
    serializer_class = CartoDBTableSerializer


class LocationTypesViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = GatewayType.objects.all()
    serializer_class = GatewayTypeSerializer


class RegionsViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Region.objects.all()
    serializer_class = RegionSerializer


class GovernoratesViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Governorate.objects.all()
    serializer_class = GovernorateSerializer


class LocalitiesViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Locality.objects.all()
    serializer_class = LocalitySerializer


class LocationsViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class LocationQuerySetView(ListAPIView):
    model = Location
    lookup_field = 'q'
    serializer_class = LocationSerializer

    def get_queryset(self):
        q = self.request.query_params.get('q')
        qs = self.model.objects
        if q:
            qs = qs.filter(name__icontains=q)

        # return maximum 7 records
        return qs.all()[:7]