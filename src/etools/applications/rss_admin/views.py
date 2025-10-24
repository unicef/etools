from django.db import connection

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.partners.filters import InterventionEditableByFilter, ShowAmendmentsFilter
from etools.applications.partners.models import Agreement, Intervention, PartnerOrganization
from etools.applications.partners.serializers.interventions_v2 import (
    InterventionCreateUpdateSerializer,
    InterventionDetailSerializer,
    InterventionListSerializer,
)
from etools.applications.partners.tasks import send_pd_to_vision
from etools.applications.rss_admin.permissions import IsRssAdmin
from etools.applications.rss_admin.serializers import (
    AgreementRssSerializer,
    BulkCloseProgrammeDocumentsSerializer,
    PartnerOrganizationRssSerializer,
)
from etools.applications.utils.pagination import AppendablePageNumberPagination
from etools.libraries.djangolib.views import FilterQueryMixin


class PartnerOrganizationRssViewSet(QueryStringFilterMixin, viewsets.ModelViewSet, FilterQueryMixin):
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationRssSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    pagination_class = AppendablePageNumberPagination
    search_fields = (
        'organization__name',
        'organization__vendor_number',
        'organization__short_name',
        'email',
        'phone_number',
    )
    ordering_fields = (
        'organization__name', 'organization__vendor_number', 'rating', 'hidden'
    )

    # PMP-style filters mapping
    filters = (
        ('partner_types', 'organization__organization_type__in'),
        ('cso_types', 'organization__cso_type__in'),
        ('risk_ratings', 'rating__in'),
        ('rating', 'rating'),
        ('hidden', 'hidden'),
        ('organization__vendor_number', 'organization__vendor_number__icontains'),
    )

    def get_queryset(self):
        qs = super().get_queryset()
        return self.apply_filter_queries(qs, self.filter_params)


class AgreementRssViewSet(QueryStringFilterMixin, viewsets.ModelViewSet, FilterQueryMixin):
    queryset = Agreement.objects.all()
    serializer_class = AgreementRssSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    pagination_class = AppendablePageNumberPagination
    search_fields = (
        'agreement_number',
        'partner__organization__name',
        'partner__organization__vendor_number',
    )
    ordering_fields = (
        'agreement_number', 'partner__organization__name', 'status', 'start', 'end'
    )

    # PMP-style filters mapping
    filters = (
        ('type', 'agreement_type__in'),
        ('types', 'agreement_type__in'),
        ('status', 'status__in'),
        ('statuses', 'status__in'),
        ('cpStructures', 'country_programme__in'),
        ('partners', 'partner__in'),
        ('start', 'start'),
        ('end', 'end'),
        ('special_conditions_pca', 'special_conditions_pca'),
    )

    def get_queryset(self):
        qs = super().get_queryset()
        return self.apply_filter_queries(qs, self.filter_params)


class ProgrammeDocumentRssViewSet(QueryStringFilterMixin, viewsets.ModelViewSet, FilterQueryMixin):
    queryset = Intervention.objects.all()
    serializer_class = InterventionListSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (
        filters.SearchFilter,
        filters.OrderingFilter,
        ShowAmendmentsFilter,
        InterventionEditableByFilter,
    )
    pagination_class = AppendablePageNumberPagination
    search_fields = (
        'number',
        'title',
        'agreement__agreement_number',
        'agreement__partner__organization__name',
        'agreement__partner__organization__vendor_number',
    )
    ordering_fields = (
        'number', 'document_type', 'status', 'title', 'start', 'end',
        'agreement__partner__organization__name'
    )

    filters = (
        ('status', 'status__in'),
        ('statuses', 'status__in'),
        ('document_type', 'document_type__in'),
        ('document_types', 'document_type__in'),
        ('sections', 'sections__in'),
        ('office', 'offices__in'),
        ('offices', 'offices__in'),
        ('donors', 'frs__fr_items__donor__icontains'),
        ('partners', 'agreement__partner__in'),
        ('grants', 'frs__fr_items__grant_number__icontains'),
        ('unicef_focal_points', 'unicef_focal_points__in'),
        ('budget_owner__in', 'budget_owner__in'),
        ('country_programme', 'country_programme__in'),
        ('country_programmes', 'country_programme__in'),
        ('cp_outputs', 'result_links__cp_output__in'),
        ('start', 'start'),
        ('end', 'end'),
        ('end_after', 'end__gte'),
        ('contingency_pd', 'contingency_pd'),
    )

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return InterventionCreateUpdateSerializer
        if self.request.method == "POST":
            return InterventionCreateUpdateSerializer
        if self.action == 'retrieve':
            return InterventionDetailSerializer
        return InterventionListSerializer

    def get_queryset(self):
        qs = Intervention.objects.frs_qs()
        return self.apply_filter_queries(qs, self.filter_params)

    def _maybe_trigger_vision_sync(self, instance, old_status=None):
        if instance.status == Intervention.SIGNED and old_status != Intervention.SIGNED:
            if not tenant_switch_is_active('disable_pd_vision_sync'):
                send_pd_to_vision.delay(connection.tenant.name, instance.pk)

    def perform_create(self, serializer):
        serializer.save()
        self._maybe_trigger_vision_sync(serializer.instance)

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        serializer.save()
        self._maybe_trigger_vision_sync(serializer.instance, old_status=old_status)

    @action(detail=False, methods=['put'], url_path='bulk-close')
    def bulk_close(self, request, *args, **kwargs):
        serializer = BulkCloseProgrammeDocumentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.update(serializer.validated_data, request.user)
        return Response(result, status=status.HTTP_200_OK)
