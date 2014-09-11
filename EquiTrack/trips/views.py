__author__ = 'jcranwellward'

from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.renderers import JSONPRenderer
from rest_framework.response import Response

from reports.models import Sector
from .models import Trip, Office
from .serializers import TripSerializer


class TripsView(ListAPIView):

    model = Trip
    renderer_classes = (JSONPRenderer,)
    serializer_class = TripSerializer

    def get_queryset(self):
        return self.model.objects.filter(
            status=self.model.APPROVED,
            travel_type=Trip.DUTY_TRAVEL
        )


class TripsByOfficeView(APIView):


    def get(self, request):

        by_office = []
        for office in Office.objects.all():
            trips = office.trip_set.filter(
                Q(status=Trip.APPROVED) |
                Q(status=Trip.COMPLETED)
            )
            office = {'name': office.name}
            for sector in Sector.objects.all():
                office[sector.name] = trips.filter(
                    section=sector).count()
            by_office.append(office)


        payload = {
            'data': by_office,
            'xkey': 'name',
            'ykeys': [sector.name for sector in Sector.objects.all()],
            'labels': [sector.name for sector in Sector.objects.all()],
            'barColors': ['#1abc9c', '#2dcc70', '#e84c3d']
        }

        return Response(data=payload)
