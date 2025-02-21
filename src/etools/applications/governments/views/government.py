from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from etools.applications.governments.models import EWPActivity, EWPKeyIntervention, EWPOutput, GovernmentEWP
from etools.applications.governments.serializers.ewp import (
    EWPKeyInterventionSerializer,
    EWPOutputSerializer,
    GovernmentEWPSerializer,
)
from etools.applications.governments.serializers.result_structure import EWPActivitySerializer
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

        if 'country_programme_id' in self.request.query_params.keys():
            return queryset.filter(country_programme_id=self.request.query_params.get('country_programme_id'))\
                .order_by('name')
        return queryset.none()


class EWPOutputListView(ListAPIView):
    """
    Returns a list of all EWPOutputs which have Workplans associated to a gdd given a query param.
    """
    queryset = EWPOutput.objects.all()
    serializer_class = EWPOutputSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = super().get_queryset()

        if 'gdd_id' in self.request.query_params.keys():
            return queryset.select_related('workplan').prefetch_related('workplan__government_gdds')\
                .filter(workplan__government_gdds=self.request.query_params.get('gdd_id'))
        return queryset.none()


class EWPKeyInterventionListView(ListAPIView):
    queryset = EWPKeyIntervention.objects.all()
    serializer_class = EWPKeyInterventionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = super().get_queryset()

        if 'ewp_output_id' in self.request.query_params.keys():
            return queryset.filter(ewp_output_id=self.request.query_params.get('ewp_output_id'))
        return queryset.none()


class EWPActivityListView(ListAPIView):
    queryset = EWPActivity.objects.all()
    serializer_class = EWPActivitySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = super().get_queryset()

        if 'ewp_key_intervention_id' in self.request.query_params.keys():
            return queryset.filter(ewp_key_intervention_id=self.request.query_params.get('ewp_key_intervention_id'))
        return queryset.none()
