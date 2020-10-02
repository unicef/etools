from etools.applications.partners.views.partner_organization_v2 import (
    PartnerOrganizationListAPIView,
    PartnerStaffMemberListAPIVIew,
)
from etools.applications.partners.views.v3 import PMPBaseViewMixin


class PMPPartnerOrganizationMixin(PMPBaseViewMixin):
    def get_queryset(self, format=None):
        return self.partners()


class PMPPartnerOrganizationListAPIView(
        PMPPartnerOrganizationMixin,
        PartnerOrganizationListAPIView,
):
    """Wrapper for Partner Organizations"""


class PMPPartnerStaffMemberMixin(PMPBaseViewMixin):
    def get_queryset(self, format=None):
        return self.queryset.filter(partner__in=self.partners())


class PMPPartnerStaffMemberListAPIVIew(
        PMPPartnerStaffMemberMixin,
        PartnerStaffMemberListAPIVIew,
):
    """Wrapper for Partner Organizations staff members"""
