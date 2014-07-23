__author__ = 'jcranwellward'

from rest_framework.generics import ListAPIView
from rest_framework.renderers import JSONPRenderer

from .models import Trip
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
