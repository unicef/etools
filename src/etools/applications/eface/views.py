from django_filters.rest_framework import DjangoFilterBackend
from etools_validator.mixins import ValidatorViewMixin
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import MultiSerializerViewSetMixin, NestedViewSetMixin, SafeTenantViewSetMixin

from etools.applications.eface.filters import EFaceFormFilterSet
from etools.applications.eface.models import EFaceForm, FormActivity
from etools.applications.eface.serializers import EFaceFormSerializer, FormActivitySerializer


class EFaceBaseViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
):
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]


class EFaceFormsViewSet(
    EFaceBaseViewSet,
    ValidatorViewMixin,
    viewsets.ModelViewSet,
):
    """
    Retrieve and Update Agreement.
    """
    queryset = EFaceForm.objects.select_related('intervention').order_by('id')
    serializer_class = EFaceFormSerializer
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter)
    filter_class = EFaceFormFilterSet
    ordering_fields = (
        'created', 'status',
    )
    search_fields = ('reference_number',)
    pagination_class = DynamicPageNumberPagination

    def get_queryset(self):
        queryset = super().get_queryset()

        if 'UNICEF User' not in [g.name for g in self.request.user.groups.all()]:
            queryset = queryset.filter(intervention__partner_focal_points__user=self.request.user).distinct()

        return queryset

    # todo: add instance validations (copy MonitoringActivitiesViewSet.create/update)


class EFaceFormActivitiesViewSet(
    EFaceBaseViewSet,
    NestedViewSetMixin,
    viewsets.ModelViewSet,
):
    queryset = FormActivity.objects.all().order_by('id')
    serializer_class = FormActivitySerializer

    def perform_create(self, serializer):
        serializer.save(form=self.get_parent_object())
