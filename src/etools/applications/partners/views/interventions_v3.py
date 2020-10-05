from copy import copy

from django.db import transaction

from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import is_success

from etools.applications.field_monitoring.permissions import IsEditAction, IsReadAction
from etools.applications.partners.models import (
    Intervention,
    InterventionAttachment,
    InterventionManagementBudget,
    InterventionRisk,
    InterventionSupplyItem,
)
from etools.applications.partners.permissions import (
    intervention_field_is_editable_permission,
    PMPInterventionPermission,
)
from etools.applications.partners.serializers.exports.interventions import (
    InterventionExportFlatSerializer,
    InterventionExportSerializer,
)
from etools.applications.partners.serializers.interventions_v2 import (
    InterventionBudgetCUSerializer,
    InterventionCreateUpdateSerializer,
    InterventionListSerializer,
    MinimalInterventionListSerializer,
)
from etools.applications.partners.serializers.interventions_v3 import (
    InterventionDetailSerializer,
    InterventionDummySerializer,
    InterventionManagementBudgetSerializer,
    InterventionRiskSerializer,
    InterventionSupplyItemSerializer,
    PMPInterventionAttachmentSerializer,
)
from etools.applications.partners.serializers.v3 import (
    PartnerInterventionLowerResultSerializer,
    UNICEFInterventionLowerResultSerializer,
)
from etools.applications.partners.views.interventions_v2 import (
    InterventionAttachmentUpdateDeleteView,
    InterventionDetailAPIView,
    InterventionIndicatorsListView,
    InterventionIndicatorsUpdateView,
    InterventionListAPIView,
    InterventionReportingRequirementView,
)
from etools.applications.partners.views.v3 import PMPBaseViewMixin
from etools.applications.reports.models import InterventionActivity, LowerResult
from etools.applications.reports.serializers.v2 import InterventionActivityDetailSerializer


class PMPInterventionMixin(PMPBaseViewMixin):
    SERIALIZER_OPTIONS = {
        "list": (InterventionListSerializer, InterventionListSerializer),
        "create": (InterventionCreateUpdateSerializer, InterventionCreateUpdateSerializer),
        "detail": (InterventionDetailSerializer, InterventionDetailSerializer),
        "list_min": (MinimalInterventionListSerializer, MinimalInterventionListSerializer),
        "csv": (InterventionExportSerializer, InterventionDummySerializer),
        "csv_flat": (InterventionExportFlatSerializer, InterventionDummySerializer),
    }

    def get_queryset(self, format=None):
        qs = super().get_queryset()
        # if partner, limit to interventions that they are associated with
        if self.is_partner_staff():
            qs = qs.filter(agreement__partner__in=self.partners())
        return qs


class DetailedInterventionResponseMixin:
    detailed_intervention_methods = ['post', 'put', 'patch']
    detailed_intervention_serializer = InterventionDetailSerializer

    def get_intervention(self) -> Intervention:
        raise NotImplementedError

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if request.method.lower() in self.detailed_intervention_methods and is_success(response.status_code):
            response.data['intervention'] = self.detailed_intervention_serializer(
                instance=self.get_intervention(),
                context=self.get_serializer_context(),
            ).data
        return response


class PMPInterventionListCreateView(PMPInterventionMixin, InterventionListAPIView):
    permission_classes = (IsAuthenticated, PMPInterventionPermission)
    search_terms = (
        'title__icontains',
        'agreement__partner__name__icontains',
        'number__icontains',
        'cfei_number__icontains',
    )

    def get_serializer_class(self):
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") in ["csv", "csv_flat"]:
                    return self.map_serializer(query_params.get("format"))
            if "verbosity" in query_params.keys():
                if query_params.get("verbosity") == 'minimal':
                    return self.map_serializer("list_min")
        if self.request.method == "POST":
            return self.map_serializer("create")
        return self.map_serializer("list")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            self.map_serializer("detail")(
                self.instance,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
            headers=self.headers
        )


class PMPInterventionRetrieveUpdateView(PMPInterventionMixin, InterventionDetailAPIView):
    SERIALIZER_MAP = copy(InterventionDetailAPIView.SERIALIZER_MAP)
    SERIALIZER_MAP.update({
        'risks': InterventionRiskSerializer,
        'planned_budget': InterventionBudgetCUSerializer,
    })
    related_fields = InterventionDetailAPIView.related_fields + [
        'risks',
        'planned_budget',
    ]

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return self.map_serializer("create")
        return self.map_serializer("detail")

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(
            self.map_serializer("detail")(
                self.instance,
                context=self.get_serializer_context(),
            ).data,
        )


class InterventionPDOutputsViewMixin(DetailedInterventionResponseMixin):
    queryset = LowerResult.objects.select_related('result_link').order_by('id')
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('pd_outputs'))
    ]

    def get_serializer_class(self):
        if 'UNICEF User' in self.request.user.groups.values_list('name', flat=True):
            return UNICEFInterventionLowerResultSerializer
        return PartnerInterventionLowerResultSerializer

    def get_root_object(self):
        if not hasattr(self, '_intervention'):
            self._intervention = Intervention.objects.filter(pk=self.kwargs.get('intervention_pk')).first()
        return self._intervention

    def get_intervention(self):
        return self.get_root_object()

    def get_serializer(self, *args, **kwargs):
        kwargs['intervention'] = self.get_root_object()
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(result_link__intervention=self.get_root_object())


class InterventionPDOutputsListCreateView(InterventionPDOutputsViewMixin, ListCreateAPIView):
    pass


class InterventionPDOutputsDetailUpdateView(InterventionPDOutputsViewMixin, RetrieveUpdateDestroyAPIView):
    pass


class PMPInterventionManagementBudgetRetrieveUpdateView(
    DetailedInterventionResponseMixin, PMPInterventionMixin, RetrieveUpdateAPIView
):
    queryset = InterventionManagementBudget.objects
    serializer_class = InterventionManagementBudgetSerializer

    def get_intervention(self):
        if not hasattr(self, '_intervention'):
            self._intervention = self.get_pd_or_404(self.kwargs.get("intervention_pk"))
        return self._intervention

    def get_object(self):
        obj, __ = InterventionManagementBudget.objects.get_or_create(
            intervention=self.get_intervention(),
        )
        return obj

    def get_serializer(self, *args, **kwargs):
        if kwargs.get("data"):
            kwargs["data"]["intervention"] = self.kwargs.get("intervention_pk")
        return super().get_serializer(*args, **kwargs)


class PMPInterventionSupplyItemListCreateView(
    DetailedInterventionResponseMixin,
    PMPInterventionMixin,
    ListCreateAPIView
):
    queryset = InterventionSupplyItem.objects
    serializer_class = InterventionSupplyItemSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            intervention=self.get_pd(self.kwargs.get("intervention_pk")),
        )

    def get_intervention(self) -> Intervention:
        return self.get_pd(self.kwargs.get("intervention_pk"))

    def get_serializer(self, *args, **kwargs):
        if kwargs.get("data"):
            kwargs["data"]["intervention"] = self.get_pd(
                self.kwargs.get("intervention_pk"),
            )
        return super().get_serializer(*args, **kwargs)


class PMPInterventionSupplyItemRetrieveUpdateView(
    DetailedInterventionResponseMixin,
    PMPInterventionMixin,
    RetrieveUpdateDestroyAPIView,
):
    queryset = InterventionSupplyItem.objects
    serializer_class = InterventionSupplyItemSerializer

    def get_intervention(self) -> Intervention:
        return self.get_pd(self.kwargs.get("intervention_pk"))


class InterventionActivityViewMixin(DetailedInterventionResponseMixin):
    queryset = InterventionActivity.objects.prefetch_related('items', 'time_frames').order_by('id')
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('pd_outputs'))
    ]
    serializer_class = InterventionActivityDetailSerializer

    def get_root_object(self):
        return Intervention.objects.filter(
            pk=self.kwargs.get('intervention_pk'),
        ).first()

    def get_intervention(self) -> Intervention:
        return self.get_root_object()

    def get_parent_object(self):
        if not hasattr(self, '_result'):
            self._result = LowerResult.objects.filter(
                result_link__intervention_id=self.kwargs.get('intervention_pk'),
                pk=self.kwargs.get('output_pk')
            ).first()
        return self._result

    def get_serializer(self, *args, **kwargs):
        kwargs['intervention'] = self.get_root_object()
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(result=self.get_parent_object())


class InterventionActivityCreateView(InterventionActivityViewMixin, CreateAPIView):
    def perform_create(self, serializer):
        serializer.save(result=self.get_parent_object())


class InterventionActivityDetailUpdateView(InterventionActivityViewMixin, RetrieveUpdateDestroyAPIView):
    pass


class InterventionRiskDeleteView(DestroyAPIView):
    queryset = InterventionRisk.objects
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('risks'))
    ]

    def get_root_object(self):
        if not hasattr(self, '_intervention'):
            self._intervention = Intervention.objects.filter(pk=self.kwargs.get('intervention_pk')).first()
        return self._intervention

    def get_queryset(self):
        return super().get_queryset().filter(intervention=self.get_root_object())


class PMPInterventionAttachmentListCreateView(DetailedInterventionResponseMixin, ListCreateAPIView):
    serializer_class = PMPInterventionAttachmentSerializer
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('attachments')),
    ]
    queryset = InterventionAttachment.objects.all()

    def get_root_object(self):
        if not hasattr(self, '_intervention'):
            self._intervention = Intervention.objects.filter(pk=self.kwargs.get('intervention_pk')).first()
        return self._intervention

    def get_queryset(self):
        return super().get_queryset().filter(intervention=self.get_root_object())

    def perform_create(self, serializer):
        serializer.save(intervention=self.get_root_object())

    def get_intervention(self) -> Intervention:
        return self.get_root_object()


class PMPInterventionAttachmentUpdateDeleteView(
    DetailedInterventionResponseMixin,
    InterventionAttachmentUpdateDeleteView,
):
    serializer_class = PMPInterventionAttachmentSerializer
    queryset = InterventionAttachment.objects.all()
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('attachments')),
    ]

    def get_root_object(self):
        if not hasattr(self, '_intervention'):
            self._intervention = Intervention.objects.filter(pk=self.kwargs.get('intervention_pk')).first()
        return self._intervention

    def get_queryset(self):
        return super().get_queryset().filter(intervention=self.get_root_object())

    def get_intervention(self) -> Intervention:
        return self.get_root_object()


class PMPInterventionIndicatorsUpdateView(
        DetailedInterventionResponseMixin,
        InterventionIndicatorsUpdateView,
):
    def get_root_object(self):
        if not hasattr(self, '_intervention'):
            self._intervention = self.get_object().lower_result.result_link.intervention
        return self._intervention

    def get_intervention(self) -> Intervention:
        return self.get_root_object()


class PMPInterventionReportingRequirementView(
        PMPInterventionMixin,
        InterventionReportingRequirementView,
):
    """Wrapper for PD reporting requirements"""


class PMPInterventionIndicatorsListView(
        PMPInterventionMixin,
        InterventionIndicatorsListView,
):
    """Wrapper for PD indicators"""
