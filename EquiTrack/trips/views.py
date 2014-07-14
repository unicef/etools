__author__ = 'jcranwellward'

from rest_framework.generics import ListAPIView

from .models import Trip


class TripsView(ListAPIView):

    model = Trip

    def get_queryset(self):
        return self.model.objects.filter(
            status=self.model.APPROVED
        )
