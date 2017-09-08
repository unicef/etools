
from rest_framework.generics import (
    RetrieveUpdateDestroyAPIView,
    ListAPIView, RetrieveAPIView, GenericAPIView)
from rest_framework_csv import renderers as r

from EquiTrack.validation_mixins import ValidatorViewMixin
from partners.exports_v2 import InterventionCvsRenderer
from partners.filters import PartnerScopeFilter

from partners.models import (
    Intervention,
)
from partners.serializers.interventions_v2 import (
    InterventionCreateUpdateSerializer,
    InterventionBudgetCUSerializer,
    PlannedVisitsCUSerializer,
    InterventionAttachmentSerializer,
    InterventionAmendmentCUSerializer,
    InterventionSectorLocationCUSerializer,
    InterventionResultCUSerializer,
)
from partners.serializers.prp_v1 import InterventionDetailSerializerV3, PRPInterventionListSerializer, \
    PDDetailsWrapperRenderer
from partners.permissions import PartneshipManagerPermission


class PRPInterventionListAPIView(ValidatorViewMixin, ListAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = PRPInterventionListSerializer
    permission_classes = (PartneshipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (PDDetailsWrapperRenderer,)

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


class PRPInterventionDetailAPIView(ValidatorViewMixin, RetrieveUpdateDestroyAPIView):
    """
    V3 of the Intervention Detail API
    """
    queryset = Intervention.objects.detail_qs().all()
    serializer_class = InterventionDetailSerializerV3
    permission_classes = (PartneshipManagerPermission,)

    SERIALIZER_MAP = {
        'planned_budget': InterventionBudgetCUSerializer,
        'planned_visits': PlannedVisitsCUSerializer,
        'attachments': InterventionAttachmentSerializer,
        'amendments': InterventionAmendmentCUSerializer,
        'sector_locations': InterventionSectorLocationCUSerializer,
        'result_links': InterventionResultCUSerializer
    }

    def get_serializer_class(self):
        """
        Use different serilizers for methods
        """
        if self.request.method in ["PATCH", "PUT"]:
            return InterventionCreateUpdateSerializer
        return super(PRPInterventionDetailAPIView, self).get_serializer_class()
