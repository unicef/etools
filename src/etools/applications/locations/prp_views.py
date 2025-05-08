from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.locations.models import Location
from etools.applications.locations.serializers import LocationExportFlatSerializer
from etools.applications.partners.filters import PartnerScopeFilter
from etools.applications.partners.permissions import ListCreateAPIMixedPermission
from etools.applications.partners.views.helpers import set_tenant_or_fail


class PRPLocationListAPIView(QueryStringFilterMixin, ListAPIView):
    """
    Returns a list of locations for a given country / workspace code
    """
    serializer_class = LocationExportFlatSerializer
    permission_classes = (ListCreateAPIMixedPermission, )
    filter_backends = (PartnerScopeFilter,)
    pagination_class = LimitOffsetPagination
    queryset = Location.simplified_geom.filter(intervention_flat_locations__isnull=False)

    filters = (
        ('admin_level', 'admin_level'),
    )

    def get_queryset(self, format=None):
        workspace = self.request.query_params.get('workspace', None)
        set_tenant_or_fail(workspace)
        return super().get_queryset()
