from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import SafeTenantViewSetMixin

from etools.applications.psea.models import Assessment
from etools.applications.psea.serializers import AssessmentSerializer


class AssessmentViewSet(
        SafeTenantViewSetMixin,
        mixins.CreateModelMixin,
        mixins.ListModelMixin,
        viewsets.GenericViewSet,
):
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]

    queryset = Assessment.objects.all()
    serializer_class = AssessmentSerializer

    filter_backends = (SearchFilter, DjangoFilterBackend, OrderingFilter)
    search_fields = ('partner__name', )
    export_filename = 'Assessment'
