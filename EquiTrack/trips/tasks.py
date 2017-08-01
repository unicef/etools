from __future__ import absolute_import

import traceback
import datetime

from django.conf import settings
from django.db.models import Q

from EquiTrack.celery import app
from EquiTrack.utils import get_current_site, get_environment

from users.models import User

from notification.models import Notification

from trips.models import Trip


@app.task
def process_trips():

    users = User.objects.filter(is_staff=True, is_active=True)
    for user in users:

        # 1. Upcoming trips (for any traveller) push notifications
        trips_coming = user.trips.filter(
            Q(status=Trip.APPROVED) | Q(status=Trip.SUBMITTED),
            from_date__gt=datetime.datetime.now()
        )

        # 2. Overdue reports send emails
        trips_overdue = user.trips.filter(
            status=Trip.APPROVED,
            to_date__lt=datetime.datetime.now())

        if trips_coming or trips_overdue and user.username == 'ntrncic':
            print(user.username)
            print settings.EMAIL_BACKEND
            print settings.POST_OFFICE_BACKEND
            print settings.CELERY_EMAIL_BACKEND
            print settings.MANDRILL_API_KEY
            trips_overdue_text = {}
            trips_coming_text = {}
            try:
                for trip in trips_overdue:
                    trips_overdue_text[trip.purpose_of_travel] = ['https://{}{}'.format(
                        get_current_site().domain,
                        trip.get_admin_url()), trip.from_date.strftime("%d-%b-%y")]

                for trip in trips_coming:
                    trips_coming_text[trip.purpose_of_travel] = ['https://{}{}'.format(
                        get_current_site().domain,
                        trip.get_admin_url()), trip.from_date.strftime("%d-%b-%y")]

                notification = Notification.objects.create(
                    sender='equitrack@unicef.org',
                    recipients=[user.email, ], template_name='trips/trip/summary',
                    template_data={
                        'trips_coming_text': trips_coming_text,
                        'trips_overdue_text': trips_overdue_text,
                        'owner_name': user.get_full_name(),
                        'environment': get_environment()
                    }
                )

                notification.send_notification()

            except Exception as exp:
                print exp.message
                print traceback.format_exc()

    return "Processing"
