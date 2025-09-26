from rest_framework import viewsets, filters

from etools.applications.partners.models import PartnerOrganization
from etools.applications.rss_admin.permissions import IsRssAdmin
from etools.applications.rss_admin.serializers import PartnerOrganizationAdminSerializer


class PartnerOrganizationAdminViewSet(viewsets.ModelViewSet):
    queryset = PartnerOrganization.objects.all()
    serializer_class = PartnerOrganizationAdminSerializer
    permission_classes = (IsRssAdmin,)
    filter_backends = (filters.SearchFilter,)
    search_fields = (
        'organization__name',
        'organization__vendor_number',
        'organization__short_name',
        'email',
        'phone_number',
    )

