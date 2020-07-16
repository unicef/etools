from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.permissions import PartnershipManagerPermission
from etools.applications.partners.serializers.exports.interventions import (
    InterventionExportFlatSerializer,
    InterventionExportSerializer,
)
from etools.applications.partners.serializers.interventions_v2 import (
    InterventionCreateUpdateSerializer,
    InterventionDetailSerializer,
    InterventionListSerializer,
    MinimalInterventionListSerializer,
)


class PMPBaseViewMixin:
    permission_classes = (PartnershipManagerPermission,)

    SERIALIZER_OPTIONS = {
        "list": (InterventionListSerializer, None),
        "create": (InterventionCreateUpdateSerializer, None),
        "detail": (InterventionDetailSerializer, None),
        "list_min": (MinimalInterventionListSerializer, None),
        "csv": (InterventionExportSerializer, None),
        "csv_flat": (InterventionExportFlatSerializer, None),
    }

    def is_partner_staff(self):
        """Flag indicator whether user is a partner"""
        return self.request.user.profile.partner_staff_member

    def partners(self):
        """List of partners user associated with"""
        if not self.is_partner_staff():
            return []
        return PartnerOrganization.objects.filter(
            staff_members__email=self.request.user.email,
        )

    def map_serializer(self, serializer):
        default_serializer, partner_serializer = self.SERIALIZER_OPTIONS.get(
            serializer,
            (None, None),
        )
        if self.is_partner_staff():
            return partner_serializer
        return default_serializer
