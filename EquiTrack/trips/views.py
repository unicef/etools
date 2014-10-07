__author__ = 'jcranwellward'

from datetime import datetime

from django.db.models import Q
from django.views.generic import TemplateView

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.renderers import JSONPRenderer
from rest_framework.response import Response

from reports.models import Sector
from .models import Trip, Office
from .serializers import TripSerializer


def get_trip_months():

    trips = Trip.objects.filter(
        Q(status=Trip.APPROVED) |
        Q(status=Trip.COMPLETED)
    )

    dates = set(trips.values_list('from_date', flat=True))

    months = list(set([datetime(date.year, date.month, 1) for date in dates]))

    return sorted(months, reverse=True)


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

        months = get_trip_months()
        month_num = request.QUERY_PARAMS.get('month', 0)
        month = months[int(month_num)]

        by_office = []
        sections = Sector.objects.filter(
            dashboard=True
        )
        for office in Office.objects.all():
            trips = office.trip_set.filter(
                Q(status=Trip.APPROVED) |
                Q(status=Trip.COMPLETED)
            ).filter(
                from_date__year=month.year,
                from_date__month=month.month
            )
            office = {'name': office.name}
            for sector in sections:
                office[sector.name] = trips.filter(
                    section=sector).count()
            by_office.append(office)

        payload = {
            'data': by_office,
            'xkey': 'name',
            'ykeys': [sector.name for sector in sections],
            'labels': [sector.name for sector in sections],
            'barColors': ['#1abc9c', '#2dcc70', '#e84c3d', '#3abc9c', '#5dcc70', '#684c3d']
        }

        return Response(data=payload)


class TripsDashboard(TemplateView):

    template_name = 'trips/dashboard.html'

    def get_context_data(self, **kwargs):

        months = get_trip_months()
        month_num = self.request.GET.get('month', 0)
        month = months[int(month_num)]

        return {
            'months': months,
            'current_month': month,
            'current_month_num': month_num,
            'trips': {
                'planned': Trip.objects.filter(
                    status=Trip.PLANNED,
                ).count(),
                'approved': Trip.objects.filter(
                    status=Trip.APPROVED,
                ).count(),
                'completed': Trip.objects.filter(
                    status=Trip.COMPLETED,
                ).count(),
                'cancelled': Trip.objects.filter(
                    status=Trip.CANCELLED,
                ).count(),
            }
        }