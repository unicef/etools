from __future__ import unicode_literals

from collections import OrderedDict

from django.db.models.query_utils import Q
from django.http.response import HttpResponse
from rest_framework import viewsets, mixins, generics, status
from rest_framework.decorators import list_route
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination as _PageNumberPagination
from rest_framework.response import Response

from .exports import TravelListExporter
from .models import Travel
from .serializers import TravelListSerializer, TravelDetailsSerializer, TravelListParameterSerializer


class PageNumberPagination(_PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('page_count', self.page.paginator.num_pages),
            ('data', data),
            ('total_count', self.page.paginator.object_list.count()),
        ]))


class TravelViewSet(mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    serializer_class = TravelListSerializer
    pagination_class = PageNumberPagination
    permission_classes = (IsAdminUser,)

    _search_fields = ('id', 'reference_number', 'traveller__first_name', 'traveller__last_name', 'purpose',
                      'section__name', 'office__name', 'supervisor__first_name', 'supervisor__last_name')

    def get_queryset(self):
        queryset = super(TravelViewSet, self).get_queryset()
        parameter_serializer = TravelListParameterSerializer(data=self.request.GET)
        if not parameter_serializer.is_valid():
            return queryset

        # Searching
        search_str = parameter_serializer.data['search']
        if search_str:
            q = Q()
            for field_name in self._search_fields:
                constructed_field_name = '{}__iexact'.format(field_name)
                q |= Q(**{constructed_field_name: search_str})
            queryset = queryset.filter(q)

        # Hide hidden travels
        show_hidden = parameter_serializer.data['show_hidden']
        if not show_hidden:
            queryset = queryset.filter(hidden=False)

        # Sorting
        prefix = '-' if parameter_serializer.data['reverse'] else ''
        sort_by = '{}{}'.format(prefix, parameter_serializer.data['sort_by'])
        return queryset.order_by(sort_by)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = TravelDetailsSerializer(instance)
        return Response(serializer.data, status.HTTP_200_OK)

    @list_route(methods=['get'])
    def export(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        dataset = TravelListExporter().export(queryset)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ModelExportPartners.csv"'
        response.write(dataset.csv)

        return response


class TravelDetailsView(mixins.RetrieveModelMixin,
                        mixins.UpdateModelMixin,
                        mixins.DestroyModelMixin,
                        generics.GenericAPIView):
    queryset = Travel.objects.all()
    serializer_class = TravelDetailsSerializer