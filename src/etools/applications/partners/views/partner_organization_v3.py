from django.db import connection

from etools.applications.partners.views.partner_organization_v2 import (
    PartnerOrganizationListAPIView,
    PartnerStaffMemberListAPIVIew,
)
from etools.applications.partners.views.v3 import PMPBaseViewMixin
from etools.applications.users.mixins import PARTNER_ACTIVE_GROUPS


class PMPPartnerOrganizationListAPIView(
        PMPBaseViewMixin,
        PartnerOrganizationListAPIView,
):
    def get_queryset(self, format=None):
        qs = super().get_queryset(format=format)

        if self.is_partner_staff():
            return qs.filter(id=self.current_partner().id)
        return qs


class PMPPartnerStaffMemberMixin(PMPBaseViewMixin):
    def get_queryset(self):
        qs = self.queryset
        if self.is_partner_staff():
            qs = qs.filter(
                realms__country=connection.tenant,
                realms__organization__partner=self.current_partner(),
                realms__group__name__in=PARTNER_ACTIVE_GROUPS,
            )
        return qs


class PMPPartnerStaffMemberListAPIVIew(
        PMPPartnerStaffMemberMixin,
        PartnerStaffMemberListAPIVIew,
):
    """Wrapper for Partner Organizations staff members"""
