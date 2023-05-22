
import functools
import operator

from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.core.renderers import FriendlyCSVRenderer
from etools.applications.t2f.filters import travel_list
from etools.applications.t2f.models import ItineraryItem, Travel, TravelActivity
from etools.applications.t2f.serializers.export import TravelActivityExportSerializer, TravelAdminExportSerializer
from etools.applications.t2f.views import T2FPagePagination


class ExportBaseView(generics.GenericAPIView):
    queryset = Travel.objects.all()
    pagination_class = T2FPagePagination
    permission_classes = (IsAdminUser,)
    filter_backends = (travel_list.TravelSearchFilter,
                       travel_list.ShowHiddenFilter,
                       travel_list.TravelSortFilter,
                       travel_list.TravelFilterBoxFilter)
    renderer_classes = (FriendlyCSVRenderer,)

    def get_renderer_context(self):
        context = super().get_renderer_context()
        context['header'] = self.serializer_class.Meta.fields
        return context


class TravelActivityExport(QueryStringFilterMixin, ExportBaseView):
    serializer_class = TravelActivityExportSerializer
    filters = (
        ('f_supervisor', 'travels__supervisor__pk__in'),
        ('f_office', 'travels__office__pk__in'),
        ('f_section', 'travels__section__pk__in'),
        ('f_status', 'travels__status__in'),
        ('f_traveler', 'travels__traveler__pk__in'),
        ('f_partner', 'partner__pk__in'),
        ('f_result', 'result__pk__in'),
        ('f_travel_type', 'travel_type__in'),
        ('f_year', ['travels__start_date__year', 'travels__end_date__year']),
        ('f_month', ['travels__start_date__month', 'travels__end_date__month']),
        ('f_location', 'locations__pk__in'),
    )

    class SimpleDTO:
        def __init__(self, travel, activity):
            self.travel = travel
            self.activity = activity

    def get_queryset(self):
        queryset = TravelActivity.objects.prefetch_related('travels', 'travels__traveler', 'travels__office', 'travels__supervisor',
                                                           'travels__section', 'locations')
        queryset = queryset.select_related(
            'partner', 'partner__organization', 'partnership', 'result', 'primary_traveler')
        queryset = queryset.order_by('id')

        queries = []
        queries.extend(self.filter_params())
        if queries:
            expression = functools.reduce(operator.and_, queries)
            queryset = queryset.filter(expression)

        return queryset.distinct()

    def get(self, request):

        queryset = self.get_queryset()

        dto_list = []
        for activity in queryset:
            for travel in activity.travels.all():
                dto_list.append(self.SimpleDTO(travel, activity))

        serializer = self.get_serializer(dto_list, many=True)
        response = Response(data=serializer.data, status=status.HTTP_200_OK)
        response['Content-Disposition'] = 'attachment; filename=Travel_{}.csv'.format(timezone.now().date())

        return response


class TravelAdminExport(ExportBaseView):
    serializer_class = TravelAdminExportSerializer

    def get(self, request):
        travel_queryset = self.filter_queryset(self.get_queryset())
        queryset = ItineraryItem.objects.filter(
            travel__in=travel_queryset).order_by('travel__reference_number', 'id')
        queryset = queryset.select_related('travel', 'travel__office', 'travel__section', 'travel__traveler',
                                           'dsa_region')
        serializer = self.get_serializer(queryset, many=True)

        response = Response(data=serializer.data, status=status.HTTP_200_OK)
        response['Content-Disposition'] = 'attachment; filename="TravelAdminExport.csv"'
        return response
