from __future__ import absolute_import

import traceback
import datetime

from django.conf import settings
from django.db.models import Q

from EquiTrack.celery import app
from EquiTrack.utils import get_environment

from users.models import User

from notification.models import Notification

from trips.models import Trip


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
            # TODO trips_overdue_text, trips_coming_text are undefined
            try:
                # for trip in trips_overdue:
                #     trips_overdue_text[trip.purpose_of_travel] = ['https://{}{}'.format(
                #         get_current_site().domain,
                #         trip.get_admin_url()), trip.from_date.strftime("%d-%b-%y")]

                # for trip in trips_coming:
                #     trips_coming_text[trip.purpose_of_travel] = ['https://{}{}'.format(
                #         get_current_site().domain,
                #         trip.get_admin_url()), trip.from_date.strftime("%d-%b-%y")]

                notification = Notification.objects.create(
                    sender='equitrack@unicef.org',
                    recipients=[user.email, ], template_name='trips/trip/summary',
                    template_data={
                        # 'trips_coming_text': trips_coming_text,
                        # 'trips_overdue_text': trips_overdue_text,
                        'owner_name': user.get_full_name(),
                        'environment': get_environment()
                    }
                )

                notification.send_notification()

            except Exception as exp:
                print exp.message
                print traceback.format_exc()

        # 1. Upcoming trips (for any traveller) push notifications
        # trips_coming_app = user.trips.filter(
        #     Q(status=Trip.APPROVED) | Q(status=Trip.SUBMITTED),
        #     from_date__range=[datetime.datetime.now() + timedelta(days=2),
        #                       datetime.datetime.now() + timedelta(days=3)]
        # )

        # # 2. Overdue reports send emails
        # for trip in trips_overdue:
        #     #post_save.connect(trip.send_trip_request, sender=Trip)
        #     print(trip.owner)
        #     trip.send_trip_request(sender=Trip)

    return "Processing"
