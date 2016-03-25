__author__ = 'unicef-leb-inn'

from rest_framework import viewsets, mixins
from rest_framework.generics import ListAPIView

from .models import CartoDBTable, GatewayType, Location
from .serializers import CartoDBTableSerializer, GatewayTypeSerializer, LocationSerializer


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


class LocationsViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Location.objects.all()
    serializer_class = LocationSerializer
