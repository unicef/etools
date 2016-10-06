
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import CursorPagination

from .models import Travel
from .serializers import TravelListSerializer, TravelDetailsSerializer


class TravelViewSet(mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    model = Travel
    serializer_class = TravelListSerializer
    pagination_class = CursorPagination
    # permission_classes = (IsAdminUser,)


class TravelDetailsViewSet(mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    model = Travel
    serializer_class = TravelDetailsSerializer