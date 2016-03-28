__author__ = 'unicef-leb-inn'

import json

from rest_framework.generics import ListAPIView
from django.views.generic.list import BaseListView

from .models import CartoDBTable, Location
from .serializers import CartoDBTableSerializer, LocationSerializer


class CartoDBTablesView(ListAPIView):
    """
    Gets a list of CartoDB tables for the mapping system
    """
    queryset = CartoDBTable.objects.all()
    serializer_class = CartoDBTableSerializer


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