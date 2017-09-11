from rest_framework.generics import (
    ListAPIView)

from EquiTrack.validation_mixins import ValidatorViewMixin
from partners.filters import PartnerScopeFilter
from partners.models import (
    Intervention,
)
from partners.serializers.interventions_v2 import (
    InterventionBudgetCUSerializer,
    PlannedVisitsCUSerializer,
    InterventionAttachmentSerializer,
    InterventionAmendmentCUSerializer,
    InterventionSectorLocationCUSerializer,
    InterventionResultCUSerializer,
)
from partners.serializers.prp_v1 import PRPInterventionListSerializer
from partners.permissions import PartneshipManagerPermission


class PRPInterventionListAPIView(ValidatorViewMixin, ListAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = PRPInterventionListSerializer
    permission_classes = (PartneshipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)

    SERIALIZER_MAP = {
        'planned_budget': InterventionBudgetCUSerializer,
        'planned_visits': PlannedVisitsCUSerializer,
        'attachments': InterventionAttachmentSerializer,
        'amendments': InterventionAmendmentCUSerializer,
        'sector_locations': InterventionSectorLocationCUSerializer,
        'result_links': InterventionResultCUSerializer
    }

    def get_queryset(self, format=None):
        q = Intervention.objects.detail_qs().all()
        # todo: add filters
        return q

    def list(self, request):
        # todo: customize this (or remove if no customizations needed)
        return super(PRPInterventionListAPIView, self).list(request)
