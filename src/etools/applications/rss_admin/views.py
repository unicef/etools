from django.db import connection

from rest_framework import filters, viewsets

from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.partners.models import Agreement, Intervention, PartnerOrganization
from etools.applications.partners.serializers.interventions_v2 import (
    InterventionCreateUpdateSerializer,
    InterventionDetailSerializer,
    InterventionListSerializer,
)
from etools.applications.partners.tasks import send_pd_to_vision
from etools.applications.rss_admin.permissions import IsRssAdmin
from etools.applications.rss_admin.serializers import AgreementRssSerializer, PartnerOrganizationRssSerializer
from etools.applications.utils.pagination import AppendablePageNumberPagination


class PartnerOrganizationRssViewSet(viewsets.ModelViewSet):
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationRssSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (filters.SearchFilter,)
    pagination_class = AppendablePageNumberPagination
    search_fields = (
        'organization__name',
        'organization__vendor_number',
        'organization__short_name',
        'email',
        'phone_number',
    )


class AgreementRssViewSet(viewsets.ModelViewSet):
    queryset = Agreement.objects.all()
    serializer_class = AgreementRssSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (filters.SearchFilter,)
    pagination_class = AppendablePageNumberPagination
    search_fields = (
        'agreement_number',
        'partner__organization__name',
        'partner__organization__vendor_number',
    )


class ProgrammeDocumentRssViewSet(viewsets.ModelViewSet):
    queryset = Intervention.objects.all()
    serializer_class = InterventionListSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (filters.SearchFilter,)
    pagination_class = AppendablePageNumberPagination
    search_fields = (
        'number',
        'title',
        'agreement__agreement_number',
        'agreement__partner__organization__name',
        'agreement__partner__organization__vendor_number',
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
        doc_type = self.request.query_params.get('document_type')
        if doc_type in (Intervention.PD, Intervention.SPD):
            qs = qs.filter(document_type=doc_type)
        return qs

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
