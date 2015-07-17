from __future__ import absolute_import

import datetime
from datetime import timedelta

from django.db.models import Q
from django.db.models.signals import post_save

from EquiTrack.celery import app
from trips.models import Trip
from trips.emails import TripSummaryEmail
from users.models import User
import json, httplib



@app.task
def process_trips():
    #TODO: Actually process trips:

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
            TripSummaryEmail(user).send('equitrack@unicef.org', user.email)

    # 1. Upcoming trips (for any traveller) push notifications
        trips_coming_app = user.trips.filter(
            Q(status=Trip.APPROVED) | Q(status=Trip.SUBMITTED),
            from_date__range=[datetime.datetime.now()+timedelta(days=2), datetime.datetime.now()+timedelta(days=3)]
        )

        for trip in trips_coming_app:
            dt = trip.from_date-datetime.date.today()
            connection = httplib.HTTPSConnection('api.parse.com', 443)
            connection.connect()
            connection.request('POST', '/1/push', json.dumps({
                "where": {
                    "installationId": trip.owner.profile.installation_id
                },
                "data": {
                    "alert": "Your trip is coming up on " + str(dt.days) + " days!"
                }
            }), {
                "X-Parse-Application-Id": "wVQDNInUSPJW7vxIB0qUtl1RPeMdBIQWbesYNqdi",
                "X-Parse-REST-API-Key": "HHWrIt4OBoeKfa3GWVisehYbtwWjr6but45rvJCr",
                "Content-Type": "application/json"
            })
            result = json.loads(connection.getresponse().read())
            print result

        # # 2. Overdue reports send emails
        # for trip in trips_overdue:
        #     #post_save.connect(trip.send_trip_request, sender=Trip)
        #     print(trip.owner)
        #     trip.send_trip_request(sender=Trip)


    return "Processing"