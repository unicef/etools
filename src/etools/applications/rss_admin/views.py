from rest_framework import filters, viewsets

from etools.applications.partners.models import Agreement, PartnerOrganization
from etools.applications.rss_admin.permissions import IsRssAdmin
from etools.applications.rss_admin.serializers import AgreementAdminSerializer, PartnerOrganizationAdminSerializer
from etools.applications.utils.pagination import AppendablePageNumberPagination


class PartnerOrganizationAdminViewSet(viewsets.ModelViewSet):
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationAdminSerializer
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


class AgreementAdminViewSet(viewsets.ModelViewSet):
    queryset = Agreement.objects.all()
    serializer_class = AgreementAdminSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (filters.SearchFilter,)
    pagination_class = AppendablePageNumberPagination
    search_fields = (
        'agreement_number',
        'partner__organization__name',
        'partner__organization__vendor_number',
    )
