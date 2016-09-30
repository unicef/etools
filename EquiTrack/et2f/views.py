
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import CursorPagination

from .models import Travel
from .serializers import TravelSerializer, TravelListViewSerializer


class TravelViewSet(mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    queryset = Travel.objects.all()
    model = Travel
    serializer_class = TravelListViewSerializer
    pagination_class = CursorPagination
    # permission_classes = (IsAdminUser,)