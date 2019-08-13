from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import SafeTenantViewSetMixin

from etools.applications.psea.models import Assessment, Assessor, Indicator
from etools.applications.psea.serializers import AssessmentSerializer, AssessorSerializer, IndicatorSerializer


class AssessmentViewSet(
        SafeTenantViewSetMixin,
        mixins.CreateModelMixin,
        mixins.ListModelMixin,
        mixins.UpdateModelMixin,
        mixins.RetrieveModelMixin,
        viewsets.GenericViewSet,
):
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]

    queryset = Assessment.objects.all()
    serializer_class = AssessmentSerializer

    filter_backends = (SearchFilter, DjangoFilterBackend, OrderingFilter)
    search_fields = ('partner__name', )
    export_filename = 'Assessment'


class AssessorViewSet(
        SafeTenantViewSetMixin,
        mixins.CreateModelMixin,
        mixins.UpdateModelMixin,
        mixins.RetrieveModelMixin,
        viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, ]
    queryset = Assessor.objects.all()
    serializer_class = AssessorSerializer


class IndicatorViewSet(
        SafeTenantViewSetMixin,
        mixins.ListModelMixin,
        viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, ]
    queryset = Indicator.objects.filter(active=True).all()
    serializer_class = IndicatorSerializer
