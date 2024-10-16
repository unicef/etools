from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView

from etools.applications.governments.models import GovernmentEWP
from etools.applications.governments.serializers.ewp import GovernmentEWPSerializer
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


class GovernmentEWPListView(ListAPIView):
    """
    Returns a list of GovernmentEWPs given a country_programme query param id
    """
    queryset = GovernmentEWP.objects.all()
    serializer_class = GovernmentEWPSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        if 'country_programme' in self.request.query_params.keys():
            return queryset.filter(country_programme=self.request.query_params.get('country_programme'))
        return queryset
