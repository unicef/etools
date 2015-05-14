from __future__ import absolute_import

from django.db.models import Q

from EquiTrack.celery import app
from trips.models import Trip
from users.models import User
from datetime import timedelta, datetime
import json, httplib



@app.task
def process_trips():
    #TODO: Actually process trips:

    users = User.objects.filter(is_staff=True, is_active=True)
    for user in users:
        #profile = user.get_profile()

        trips_coming = user.trips.filter(
            Q(status=Trip.APPROVED) | Q(status=Trip.SUBMITTED),
            from_date__gt=datetime.now())

        trips_overdue = user.trips.filter(
            status=Trip.APPROVED,
            to_date__gt=datetime.now())

    # 1. Upcoming trips (for any traveller) push notifications
        trips_coming_app = user.trips.filter(
            Q(status=Trip.APPROVED) | Q(status=Trip.SUBMITTED),
            from_date__range=[datetime.now()+timedelta(days=2), datetime.now()+timedelta(days=3)]
        )

        for trip in trips_coming_app:
            print(trip.purpose_of_travel)
            connection=httplib.HTTPSConnection('api.parse.com', 443)
            connection.connect()
            connection.request('POST', '/1/push', json.dumps({
                "where": {
                    "installationId": trip.owner.profile.installation_id
                },
                "data": {
                    "alert": "Yor trip " + trip.purpose_of_travel + " is coming up!"
                }
            }), {
                "X-Parse-Application-Id": "wVQDNInUSPJW7vxIB0qUtl1RPeMdBIQWbesYNqdi",
                "X-Parse-REST-API-Key": "HHWrIt4OBoeKfa3GWVisehYbtwWjr6but45rvJCr",
                "Content-Type": "application/json"
            })
            result = json.loads(connection.getresponse().read())
            print result

        # # 2. Overdue reports greater than 15 days
        # trips_overdue = Trip.objects.filter(
        #     status=Trip.APPROVED,
        #     to_date__gte=datetime.now()-timedelta(days=15)
        # )

        # for trip in trips_overdue:
        #     trip.send_trip_request(sender=Trip)

    return "Processing"