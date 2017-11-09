from __future__ import unicode_literals

from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from rest_framework_csv import renderers

from t2f.filters import travel_list
from t2f.serializers.export import TravelActivityExportSerializer, FinanceExportSerializer, \
    TravelAdminExportSerializer, InvoiceExportSerializer

from t2f.models import Travel, ItineraryItem, InvoiceItem, TravelActivity
from t2f.views import T2FPagePagination


class ExportBaseView(generics.GenericAPIView):
    queryset = Travel.objects.all()
    pagination_class = T2FPagePagination
    permission_classes = (IsAdminUser,)
    filter_backends = (travel_list.TravelSearchFilter,
                       travel_list.ShowHiddenFilter,
                       travel_list.TravelSortFilter,
                       travel_list.TravelFilterBoxFilter)
    renderer_classes = (renderers.CSVRenderer,)

    def get_renderer_context(self):
        context = super(ExportBaseView, self).get_renderer_context()
        context['header'] = self.serializer_class.Meta.fields
        return context


class TravelActivityExport(ExportBaseView):
    serializer_class = TravelActivityExportSerializer

    class SimpleDTO(object):
        def __init__(self, travel, activity):
            self.travel = travel
            self.activity = activity

    def get(self, request):
        queryset = TravelActivity.objects.prefetch_related('travels', 'travels__traveler', 'travels__office',
                                                           'travels__section', 'locations')
        queryset = queryset.select_related('partner', 'partnership', 'result', 'primary_traveler')
        queryset = queryset.order_by('id')
        dto_list = []
        for activity in queryset:
            for travel in activity.travels.all():
                dto_list.append(self.SimpleDTO(travel, activity))

        serializer = self.get_serializer(dto_list, many=True)

        response = Response(data=serializer.data, status=status.HTTP_200_OK)
        response['Content-Disposition'] = 'attachment; filename="TravelActivityExport.csv"'
        return response


class FinanceExport(ExportBaseView):
    serializer_class = FinanceExportSerializer

    def get(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.select_related('traveler', 'office', 'section', 'supervisor')
        serializer = self.get_serializer(queryset, many=True)

        response = Response(data=serializer.data, status=status.HTTP_200_OK)
        response['Content-Disposition'] = 'attachment; filename="FinanceExport.csv"'
        return response


class TravelAdminExport(ExportBaseView):
    serializer_class = TravelAdminExportSerializer

    def get(self, request):
        travel_queryset = self.filter_queryset(self.get_queryset())
        queryset = ItineraryItem.objects.filter(travel__in=travel_queryset).order_by('travel__reference_number', 'id')
        queryset = queryset.select_related('travel', 'travel__office', 'travel__section', 'travel__traveler',
                                           'dsa_region')
        serializer = self.get_serializer(queryset, many=True)

        response = Response(data=serializer.data, status=status.HTTP_200_OK)
        response['Content-Disposition'] = 'attachment; filename="TravelAdminExport.csv"'
        return response


class InvoiceExport(ExportBaseView):
    serializer_class = InvoiceExportSerializer

    def get(self, request):
        travel_queryset = self.filter_queryset(self.get_queryset())
        queryset = InvoiceItem.objects.filter(invoice__travel__in=travel_queryset)
        queryset = queryset.order_by('invoice__travel__reference_number', 'id')
        queryset = queryset.select_related('invoice', 'invoice__travel', 'invoice__currency', 'wbs', 'grant', 'fund')

        serializer = self.get_serializer(queryset, many=True)

        response = Response(data=serializer.data, status=status.HTTP_200_OK)
        response['Content-Disposition'] = 'attachment; filename="InvoiceExport.csv"'
        return response
