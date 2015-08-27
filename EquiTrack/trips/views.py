__author__ = 'jcranwellward'

import json
from datetime import datetime

from django.db.models import Q
from django.contrib.auth import get_user_model
from django.views.generic import FormView
from django.core import serializers

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.renderers import JSONPRenderer
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication
from rest_framework import status


from users.models import UserProfile
from reports.models import Sector
from .models import Trip, Office, ActionPoint
from .serializers import TripSerializer
from .forms import TripFilterByDateForm

User = get_user_model()


def get_trip_months():

    trips = Trip.objects.filter(
        Q(status=Trip.APPROVED) |
        Q(status=Trip.COMPLETED)
    )

    dates = set(trips.values_list('from_date', flat=True))

    months = list(set([datetime(date.year, date.month, 1) for date in dates]))

    return sorted(months, reverse=True)


class TripsApprovedView(ListAPIView):

    model = Trip
    renderer_classes = (JSONPRenderer,)
    serializer_class = TripSerializer

    def get_queryset(self):
        return self.model.objects.filter(
            status=self.model.APPROVED,
        )


class TripsApi(ListAPIView):

    model = Trip
    serializer_class = TripSerializer
    authentication_classes = (BasicAuthentication,)

    def get_queryset(self):
        user = self.request.user
        trips = Trip.get_all_trips(user)
        return trips


class TripActionView(RetrieveAPIView):

    model = Trip
    lookup_url_kwarg = 'trip'

    def retrieve(self, request, *args, **kwargs):
        trip = self.get_object()
        action = self.kwargs.get('action', None)
        user = self.request.user
        trips = Trip.get_all_trips(user)
        serializer = TripSerializer(trips, many=True)

        if action == 'submit':
            if trip.status != Trip.SUBMITTED:
                trip.status = Trip.SUBMITTED
                trip.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
        elif action == 'approve':
            trip.approved_by_supervisor = True
            trip.date_supervisor_approved = datetime.now()
            trip.save()
            return Response(serializer.data, status=status.HTTP_200_OK,)
        return Response(serializer.data, Zstatus=status.HTTP_204_NO_CONTENT)


class TripsByOfficeView(APIView):

    def get(self, request):

        months = get_trip_months()
        months.append(None)
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
            ).all()
            if month is not None:
                trips = office.trip_set.filter(
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
            'barColors': [sector.color for sector in sections]
        }

        return Response(data=payload)


class TripsDashboard(FormView):

    template_name = 'trips/dashboard.html'
    form_class = TripFilterByDateForm

    def form_valid(self, form):

        return super(TripsDashboard, self).form_valid(form)

    def get_context_data(self, **kwargs):

        months = get_trip_months()
        months.append(None)
        month_num = self.request.GET.get('month', 0)
        month = months[int(month_num)]

        by_month = []
        for section in Sector.objects.filter(
                dashboard=True
        ):
            trips = section.trip_set.all()
            if month is not None:
                trips = section.trip_set.filter(
                    from_date__year=month.year,
                    from_date__month=month.month
                )

            user_profiles = UserProfile.objects.filter(
                section=section,
                user__is_active=True
            )
            action_points = 0
            closed_action_points = 0
            for profile in user_profiles:
                action_points += profile.user.for_action.count()
                closed_action_points += profile.user.for_action.filter(status='closed').count()
            row = {
                'section': section.name,
                'color': section.color,
                'total_approved': trips.filter(
                    status=Trip.APPROVED
                ).count(),
                'total_completed': trips.filter(
                    status=Trip.COMPLETED
                ).count(),
                'actions': action_points,
                'closed_actions': closed_action_points
            }
            by_month.append(row)

        kwargs.update({
            'months': months,
            'current_month': month,
            'current_month_num': month_num,
            'trips': {
                'planned': Trip.objects.filter(
                    Q(status=Trip.PLANNED) |
                    Q(status=Trip.SUBMITTED)
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
            },
            'by_month': by_month,
        })

        return super(TripsDashboard, self).get_context_data(**kwargs)