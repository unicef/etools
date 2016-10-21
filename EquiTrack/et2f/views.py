from __future__ import unicode_literals

from collections import OrderedDict

from rest_framework import viewsets, mixins, generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination as _PageNumberPagination
from rest_framework.response import Response

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

    def get_queryset(self):
        queryset = super(TravelViewSet, self).get_queryset()
        parameter_serializer = TravelListParameterSerializer(data=self.request.GET)
        if not parameter_serializer.is_valid():
            return queryset

        prefix = '-' if parameter_serializer.data['reverse'] else ''
        sort_by = '{}{}'.format(prefix, parameter_serializer.data['sort_by'])
        return queryset.order_by(sort_by)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = TravelDetailsSerializer(instance)
        return Response(serializer.data, status.HTTP_200_OK)


class TravelDetailsView(generics.GenericAPIView):
    queryset = Travel.objects.all()
    serializer_class = TravelDetailsSerializer