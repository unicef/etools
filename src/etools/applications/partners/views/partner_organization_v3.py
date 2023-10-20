from django.shortcuts import get_object_or_404

from rest_framework.generics import ListAPIView
from rest_framework_csv import renderers as r

from etools.applications.core.mixins import ExportModelMixin
from etools.applications.core.renderers import CSVFlatRenderer
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.permissions import AllowSafeAuthenticated
from etools.applications.partners.serializers.exports.partner_organization import (
    PartnerStaffMemberExportFlatSerializer,
    PartnerStaffMemberExportSerializer,
)
from etools.applications.partners.serializers.partner_organization_v2 import PartnerStaffMemberRealmSerializer
from etools.applications.partners.views.partner_organization_v2 import PartnerOrganizationListAPIView
from etools.applications.partners.views.v3 import PMPBaseViewMixin
from etools.applications.users.models import User
from etools.libraries.djangolib.views import ExternalModuleFilterMixin


class PMPPartnerOrganizationListAPIView(
        PMPBaseViewMixin,
        PartnerOrganizationListAPIView,
):
    def get_queryset(self, format=None):
        qs = super().get_queryset(format=format)

        if self.is_partner_staff():
            return qs.filter(id=self.current_partner().id)
        return qs


class PMPPartnerStaffMemberListAPIVIew(
        PMPBaseViewMixin, ExternalModuleFilterMixin, ExportModelMixin, ListAPIView):
    """
    Returns a list of all Partner staff members
    """
    queryset = User.objects.base_qs().select_related('profile')
    serializer_class = PartnerStaffMemberRealmSerializer
    permission_classes = (AllowSafeAuthenticated,)
    renderer_classes = (
        r.JSONRenderer,
        r.CSVRenderer,
        CSVFlatRenderer,
    )
    module2filters = {
        'psea': ['partner__psea_assessment__assessor__auditor_firm_staff__user',
                 'partner__psea_assessment__assessor__user']
    }

    def get_serializer_class(self, format=None):
        """
        Use restricted field set for listing
        """
        query_params = self.request.query_params
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                return PartnerStaffMemberExportSerializer
            if query_params.get("format") == 'csv_flat':
                return PartnerStaffMemberExportFlatSerializer
        return super().get_serializer_class()

    def get_queryset(self, module=None):
        if self.request.parser_context['kwargs'] and 'partner_pk' in self.request.parser_context['kwargs']:
            partner = get_object_or_404(PartnerOrganization, pk=self.request.parser_context['kwargs']['partner_pk'])
            qs = partner.all_staff_members

            if (not self.is_partner_staff() and self.request.user.is_unicef_user()) or \
                    (self.is_partner_staff() and partner == self.current_partner()):
                return qs

            return self.queryset.none()

        return self.queryset.none()
