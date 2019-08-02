from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import SafeTenantViewSetMixin

from .models import PSEA
from .serializers import PSEASerializer


class PSEAViewSet(SafeTenantViewSetMixin, mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]

    queryset = PSEA.objects.all()
    serializer_class = PSEASerializer

    filter_backends = (SearchFilter, DjangoFilterBackend, OrderingFilter)
    search_fields = ('partner__name', )
    export_filename = 'PSEA'
