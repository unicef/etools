__author__ = 'jcranwellward'

import datetime
import logging

from django.db.models import Q
from django.contrib.auth import get_user_model
from django.views.generic import FormView, TemplateView, View
from django.http import HttpResponse
from django.conf import settings

from rest_framework import viewsets, mixins
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    RetrieveUpdateDestroyAPIView
)
from rest_framework.views import APIView
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    ParseError,
)
from rest_framework.parsers import MultiPartParser, FormParser

from users.models import UserProfile, Office, Section
from locations.models import get_random_color
from partners.models import FileType
from .models import Trip, FileAttachment
from .serializers import TripSerializer, Trip2Serializer, FileAttachmentSerializer
from .forms import TripFilterByDateForm
from rest_framework import status

User = get_user_model()


def get_trip_months():

    trips = Trip.objects.filter(
        Q(status=Trip.APPROVED) |
        Q(status=Trip.COMPLETED)
    )

    dates = set(trips.values_list('from_date', flat=True))

    months = list(set([datetime.datetime(date.year, date.month, 1) for date in dates]))

    return sorted(months, reverse=True)


class AppsTemplateView(TemplateView):
    template_name = "trips/apps/apps.html"


class AppsIOSTemplateView(TemplateView):
    template_name = "trips/apps/apps_ios.html"


class AppsAndroidTemplateView(TemplateView):
    template_name = "trips/apps/apps_android.html"


class AppsIOSPlistView(View):

    def get(self, request):
        # not serving this as a static file in case in the future we want to be able to change versions
        with open(settings.SITE_ROOT + '/templates/trips/apps/etrips.plist', 'r') as my_f:
            result = my_f.read()

        return HttpResponse(result, content_type="application/octet-stream")


class Trips2ViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = Trip.objects.all()
    serializer_class = Trip2Serializer

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        partners = request.data['partners']
        pcas = request.data['pcas']

        serializer.instance = serializer.save()
        data = serializer.data

        try:
            for partner in partners:
                serializer.instance.partners.add(partner)

            for pca in pcas:
                serializer.instance.pcas.add(pca)

            serializer.save()
        except Exception:
            pass

        headers = self.get_success_headers(serializer.data)
        return Response(data, status=status.HTTP_201_CREATED,
                        headers=headers)


class TripFileViewSet(mixins.RetrieveModelMixin,
                      mixins.ListModelMixin,
                      mixins.CreateModelMixin,
                      viewsets.GenericViewSet):

    queryset = FileAttachment.objects.all()
    serializer_class = FileAttachmentSerializer
    parser_classes = (MultiPartParser, FormParser,)

    def get_queryset(self):

        queryset = super(TripFileViewSet, self).get_queryset()
        trip_id = self.kwargs.get('trip_id')
        return queryset.filter(trip=trip_id)


class TripsViewSet(mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):

    model = Trip
    lookup_url_kwarg = 'trip'
    serializer_class = TripSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        user = self.request.user
        trips = Trip.get_current_trips(user)
        return trips

    @detail_route(methods=['post'])
    def upload(self, request, **kwargs):

        # get the file object
        file_obj = request.data.get('file')
        logging.info("File received: {}".format(file_obj))
        if not file_obj:
            raise ParseError(detail="No file was sent.")

        caption = request.data.get('caption')
        logging.info("Caption received :{}".format(caption))

        # get the trip id from the url
        trip = self.get_object()

        # the file field automatically adds incremental numbers
        mime_types = {"image/jpeg": "jpeg",
                      "image/png": "png"}

        if mime_types.get(file_obj.content_type):
            ext = mime_types.get(file_obj.content_type)
        else:
            raise ParseError(detail="File type not supported")

        # format it "picture_01.jpg" this way will be making the file easier to search
        # if the file doesn't get auto_incremented use this:
        # file_obj.name = "picture_"+ str(trip.files.count()) + "." + ext
        file_obj.name = "picture." + ext

        # get the picture type
        picture_type, created = FileType.objects.get_or_create(name='Picture')

        # create the FileAttachment object
        # TODO: desperate need of validation here: need to check if file is indeed a valid picture type
        # TODO: potentially process the image at this point to reduce size / create thumbnails
        my_file_attachment = {
            "report": file_obj,
            "type": picture_type,
            "trip": trip
        }
        if caption:
            my_file_attachment['caption'] = caption

        FileAttachment.objects.create(**my_file_attachment)

        # TODO: return a more meaningful response
        return Response(status=204)

    @detail_route(methods=['post'], url_path='(?P<action>\D+)')
    def action(self, request, *args, **kwargs):
        action = kwargs.get('action', False)
        current_user = self.request.user

        # for now... hardcoding some validation in here.
        if action not in [
            "approved",
            "submitted",
            "cancelled",
            "completed"
        ]:
            raise ParseError(detail="action must be a valid action")

        trip = self.get_object()

        # some more hard-coded validation:
        if current_user.id not in [trip.owner.id, trip.supervisor.id]:
            raise PermissionDenied(detail="You must be the traveller or the supervisor to change the status of the trip")

        if action == 'approved':
            # make sure the current user is the supervisor:
            # maybe in the future allow an admin to make this change as well.
            if not current_user.id == trip.supervisor.id:
                raise PermissionDenied(detail="You must be the supervisor to approve this trip")

            data = {"approved_by_supervisor": True,
                    "date_supervisor_approved": datetime.date.today()}

        elif action == 'completed':

            if trip.status != Trip.APPROVED:
                raise ParseError(
                    detail='The trip has to be previously approved in order to complete it'
                )

            if not trip.main_observations and trip.travel_type != Trip.STAFF_ENTITLEMENT:
                raise ParseError(
                    detail='You must provide a narrative report before the trip can be completed'
                )

            if trip.ta_required and trip.ta_trip_took_place_as_planned is False and current_user != trip.programme_assistant:
                raise ParseError(
                    detail='Only the TA travel assistant can complete the trip'
                )
            data = {
                "status": action,
            }

        else:
            data = {"status": action,
                    "approved_by_supervisor": False,
                    "approved_date": None,
                    "date_supervisor_approved": None}

        serializer = self.get_serializer(data=data,
                                         instance=trip,
                                         partial=True)

        if not serializer.is_valid():
            raise ParseError(detail="data submitted is not valid")
        serializer.save()

        return Response(serializer.data)


class TripsByOfficeView(APIView):
    """
    Returns an object used for the chart library on the trips dashboard
    """
    def get(self, request):

        months = get_trip_months()
        months.append(None)
        month_num = request.query_params.get('month', 0)
        month = months[int(month_num)]

        by_office = []
        section_ids = Trip.objects.all().values_list(
            'section', flat=True
        )
        office_ids = Trip.objects.all().values_list(
            'office', flat=True
        )
        sections = Section.objects.filter(id__in=section_ids)
        for office in Office.objects.filter(id__in=office_ids):
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
            for section in sections:
                office[section.name] = trips.filter(
                    section=section).count()
            by_office.append(office)

        payload = {
            'data': by_office,
            'xkey': 'name',
            'ykeys': [section.name for section in sections],
            'labels': [section.name for section in sections],
            'barColors': [get_random_color() for section in sections]
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
        section_ids = Trip.objects.all().values_list(
        	'section', flat=True)
        for section in Section.objects.filter(
            id__in=section_ids
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
                'color': get_random_color(),
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

        trips = Trip.objects.all()
        if month is not None:
            trips = trips.filter(
                    from_date__year=month.year,
                    from_date__month=month.month
                )

        kwargs.update({
            'months': months,
            'current_month': month,
            'current_month_num': month_num,
            'trips': {
                'planned': trips.filter(
                    Q(status=Trip.PLANNED) |
                    Q(status=Trip.SUBMITTED),
                ).count(),
                'approved': trips.filter(
                    status=Trip.APPROVED,
                ).count(),
                'completed': trips.filter(
                    status=Trip.COMPLETED,
                ).count(),
                'cancelled': trips.filter(
                    status=Trip.CANCELLED,
                ).count(),
            },
            'by_month': by_month,
        })

        return super(TripsDashboard, self).get_context_data(**kwargs)


# TODO: remove these when eTrips application was rolled out

class TripUploadPictureView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, **kwargs):

        # get the file object
        file_obj = request.data.get('file')
        logging.info("File received: {}".format(file_obj))
        if not file_obj:
            raise ParseError(detail="No file was sent.")

        caption = request.data.get('caption')
        logging.info("Caption received :{}".format(caption))

        # get the trip id from the url
        trip_id = kwargs.get("trip")
        trip = Trip.objects.filter(pk=trip_id).get()

        # the file field automatically adds incremental numbers
        mime_types = {"image/jpeg": "jpeg",
                      "image/png": "png"}

        if mime_types.get(file_obj.content_type):
            ext = mime_types.get(file_obj.content_type)
        else:
            raise ParseError(detail="File type not supported")

        # format it "picture_01.jpg" this way will be making the file easier to search
        # if the file doesn't get auto_incremented use this:
        # file_obj.name = "picture_"+ str(trip.files.count()) + "." + ext
        file_obj.name = "picture." + ext

        # get the picture type
        picture_type, created = FileType.objects.get_or_create(name='Picture')

        # create the FileAttachment object
        # TODO: desperate need of validation here: need to check if file is indeed a valid picture type
        # TODO: potentially process the image at this point to reduce size / create thumbnails
        my_file_attachment = {
            "report": file_obj,
            "type": picture_type,
            "trip": trip
        }
        if caption:
            my_file_attachment['caption'] = caption

        FileAttachment.objects.create(**my_file_attachment)

        # TODO: return a more meaningful response
        return Response(status=204)


class TripsListApi(ListAPIView):

    model = Trip
    serializer_class = TripSerializer

    def get_queryset(self):
        user = self.request.user
        trips = Trip.get_all_trips(user)
        return trips


class TripDetailsView(RetrieveUpdateDestroyAPIView):
    model = Trip
    serializer_class = TripSerializer
    lookup_url_kwarg = 'trip'
    queryset = Trip.objects.all()


class TripActionView(GenericAPIView):

    model = Trip
    serializer_class = TripSerializer

    lookup_url_kwarg = 'trip'
    queryset = Trip.objects.all()

    def post(self, request, *args, **kwargs):
        action = kwargs.get('action', False)
        current_user = self.request.user

        # for now... hardcoding some validation in here.
        if action not in [
            "approved",
            "submitted",
            "cancelled",
            "completed"
        ]:
            raise ParseError(detail="action must be a valid action")

        trip = self.get_object()

        # some more hard-coded validation:
        if current_user.id not in [trip.owner.id, trip.supervisor.id]:
            raise PermissionDenied(detail="You must be the traveller or the supervisor to change the status of the trip")

        if action == 'approved':
            # make sure the current user is the supervisor:
            # maybe in the future allow an admin to make this change as well.
            if not current_user.id == trip.supervisor.id:
                raise PermissionDenied(detail="You must be the supervisor to approve this trip")

            data = {"approved_by_supervisor": True,
                    "date_supervisor_approved": datetime.date.today()}

        elif action == 'completed':

            if trip.status != Trip.APPROVED:
                raise ParseError(
                    detail='The trip has to be previously approved in order to complete it'
                )

            if not trip.main_observations and trip.travel_type != Trip.STAFF_ENTITLEMENT:
                raise ParseError(
                    detail='You must provide a narrative report before the trip can be completed'
                )

            if trip.ta_required and trip.ta_trip_took_place_as_planned is False and current_user != trip.programme_assistant:
                raise ParseError(
                    detail='Only the TA travel assistant can complete the trip'
                )
            data = {
                "status": action,
            }

        else:
            data = {"status": action,
                    "approved_by_supervisor": False,
                    "approved_date": None,
                    "date_supervisor_approved": None}

        serializer = self.get_serializer(data=data,
                                         instance=trip,
                                         partial=True)

        if not serializer.is_valid():
            raise ParseError(detail="data submitted is not valid")
        serializer.save()

        return Response(serializer.data)