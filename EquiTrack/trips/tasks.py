from __future__ import absolute_import

import traceback
import datetime
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.db.models.signals import post_save

from EquiTrack.celery import app
from trips.models import Trip
from trips.emails import TripSummaryEmail
from users.models import User


@app.task
def process_trips():

    users = User.objects.filter(is_staff=True, is_active=True)
    for user in users:

        trips_coming = user.trips.filter(
            Q(status=Trip.APPROVED) | Q(status=Trip.SUBMITTED),
            from_date__gt=datetime.datetime.now()
        )

        trips_overdue = user.trips.filter(
            status=Trip.APPROVED,
            to_date__lt=datetime.datetime.now())

        if trips_coming or trips_overdue and user.username == 'ntrncic':
            print(user.username)
            print settings.EMAIL_BACKEND
            print settings.POST_OFFICE_BACKEND
            print settings.CELERY_EMAIL_BACKEND
            print settings.MANDRILL_API_KEY
            try:
                TripSummaryEmail(user).send('equitrack@unicef.org', user.email)
            except Exception as exp:
                print exp.message
                print traceback.format_exc()

        # 1. Upcoming trips (for any traveller) push notifications
        trips_coming_app = user.trips.filter(
            Q(status=Trip.APPROVED) | Q(status=Trip.SUBMITTED),
            from_date__range=[datetime.datetime.now()+timedelta(days=2),
                              datetime.datetime.now()+timedelta(days=3)]
        )

        # # 2. Overdue reports send emails
        # for trip in trips_overdue:
        #     #post_save.connect(trip.send_trip_request, sender=Trip)
        #     print(trip.owner)
        #     trip.send_trip_request(sender=Trip)

    return "Processing"
