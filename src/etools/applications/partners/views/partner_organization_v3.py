from etools.applications.partners.serializers.exports.partner_organization import (
    PartnerOrganizationExportFlatSerializer,
    PartnerOrganizationExportSerializer,
)
from etools.applications.partners.serializers.partner_organization_v2 import (
    MinimalPartnerOrganizationListSerializer,
    PartnerOrganizationCreateUpdateSerializer,
    PartnerOrganizationDetailSerializer,
    PartnerOrganizationListSerializer,
)
from etools.applications.partners.serializers.partner_organization_v3 import PartnerOrganizationDummySerializer
from etools.applications.partners.views.partner_organization_v2 import PartnerOrganizationListAPIView
from etools.applications.partners.views.v3 import PMPBaseViewMixin


class PMPpartnerOrganizationMixin(PMPBaseViewMixin):
    SERIALIZER_OPTIONS = {
        "list": (PartnerOrganizationListSerializer, PartnerOrganizationListSerializer),
        "create": (PartnerOrganizationCreateUpdateSerializer, PartnerOrganizationDummySerializer),
        "detail": (PartnerOrganizationDetailSerializer, PartnerOrganizationDetailSerializer),
        "list_min": (MinimalPartnerOrganizationListSerializer, MinimalPartnerOrganizationListSerializer),
        "csv": (PartnerOrganizationExportSerializer, PartnerOrganizationDummySerializer),
        "csv_flat": (PartnerOrganizationExportFlatSerializer, PartnerOrganizationDummySerializer),
    }

    def get_queryset(self, format=None):
        return self.partners()


class PMPpartnerOrganizationListAPIView(
        PMPpartnerOrganizationMixin,
        PartnerOrganizationListAPIView
):
    """Wrapper for Partner Organizations"""
