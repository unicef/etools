from collections import OrderedDict

from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination as _PageNumberPagination
from rest_framework.response import Response

from .models import Travel
from .serializers import TravelListSerializer, TravelDetailsSerializer


class PageNumberPagination(_PageNumberPagination):
    page_size = 50

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('page_count', self.page.paginator.count),
            ('data', data)
        ]))


class TravelViewSet(mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    serializer_class = TravelListSerializer
    pagination_class = PageNumberPagination
    permission_classes = (IsAdminUser,)


class TravelDetailsViewSet(mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    serializer_class = TravelDetailsSerializer