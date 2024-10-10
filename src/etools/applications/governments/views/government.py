from rest_framework.filters import OrderingFilter

from etools.applications.organizations.models import OrganizationType
from etools.applications.partners.views.partner_organization_v3 import (
    PMPPartnerOrganizationListAPIView,
    PMPPartnerStaffMemberListAPIVIew,
)


class GovernmentOrganizationListAPIView(PMPPartnerOrganizationListAPIView):
        filter_backends = PMPPartnerOrganizationListAPIView.filter_backends + (OrderingFilter,)
        ordering_fields = ('name', 'vendor_number')

        def get_queryset(self, format=None):
            qs = super().get_queryset(format=format).filter(organization__organization_type=OrganizationType.GOVERNMENT)

            if self.is_partner_staff():
                return qs.filter(id=self.current_partner().id)
            return qs


class GovernmentStaffMemberListAPIVIew(PMPPartnerStaffMemberListAPIVIew):
    module2filters = {}
