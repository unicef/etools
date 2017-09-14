from rest_framework.generics import (
    ListAPIView)

from partners.filters import PartnerScopeFilter
from partners.models import (
    Intervention,
)
from partners.serializers.prp_v1 import PRPInterventionListSerializer
from partners.permissions import PartneshipManagerPermission


class PRPInterventionListAPIView(ListAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = PRPInterventionListSerializer
    permission_classes = (PartneshipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)

    def get_queryset(self, format=None):
        q = Intervention.objects.detail_qs().all()
        # todo: add filters
        return q

    def list(self, request):
        # todo: customize this (or remove if no customizations needed)
        return super(PRPInterventionListAPIView, self).list(request)
