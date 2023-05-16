from rest_framework.generics import ListAPIView
from rest_framework_csv import renderers as r

from etools.applications.core.mixins import ExportModelMixin
from etools.applications.core.renderers import CSVFlatRenderer
from etools.applications.partners.filters import PartnerScopeFilter
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


class PMPPartnerStaffMemberMixin(PMPBaseViewMixin):
    def get_queryset(self):
        qs = self.queryset
        if self.is_partner_staff():
            qs = qs.filter(
                realms__organization__partner=self.current_partner(),
            ).distinct()
        return qs


class PMPPartnerStaffMemberListAPIVIew(
        PMPPartnerStaffMemberMixin, ExternalModuleFilterMixin, ExportModelMixin, ListAPIView):
    """
    Returns a list of all Partner staff members
    """
    queryset = User.objects.all()
    serializer_class = PartnerStaffMemberRealmSerializer
    permission_classes = (AllowSafeAuthenticated,)
    filter_backends = (PartnerScopeFilter,)
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
