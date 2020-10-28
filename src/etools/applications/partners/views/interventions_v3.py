from copy import copy

from django.db import transaction

from easy_pdf.rendering import render_to_pdf_response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import is_success
from rest_framework.views import APIView

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
    PartnershipManagerPermission,
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
    InterventionManagementBudgetSerializer,
    InterventionRiskSerializer,
    InterventionSupplyItemSerializer,
    InterventionSupplyItemUploadSerializer,
    PMPInterventionAttachmentSerializer,
)
from etools.applications.partners.serializers.v3 import (
    PartnerInterventionLowerResultSerializer,
    UNICEFInterventionLowerResultSerializer,
)
from etools.applications.partners.views.interventions_v2 import (
    InterventionAttachmentUpdateDeleteView,
    InterventionDeleteView,
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
    def get_partner_staff_qs(self, qs):
        return qs.filter(
            agreement__partner__in=self.partners(),
            date_sent_to_partner__isnull=False,
        )

    def get_queryset(self, format=None):
        qs = super().get_queryset()
        # if partner, limit to interventions that they are associated with
        if self.is_partner_staff():
            qs = self.get_partner_staff_qs(qs)
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
                export_format = query_params.get("format")
                if export_format == "csv":
                    return InterventionExportSerializer
                elif export_format == "csv_flat":
                    return InterventionExportFlatSerializer
            if "verbosity" in query_params.keys():
                if query_params.get("verbosity") == 'minimal':
                    return MinimalInterventionListSerializer
        if self.request.method == "POST":
            return InterventionCreateUpdateSerializer
        return InterventionListSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            InterventionDetailSerializer(
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
            return InterventionCreateUpdateSerializer
        return InterventionDetailSerializer

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(
            InterventionDetailSerializer(
                self.instance,
                context=self.get_serializer_context(),
            ).data,
        )


class PMPInterventionPDFView(PMPInterventionMixin, RetrieveAPIView):
    queryset = Intervention.objects.detail_qs().all()
    permission_classes = (PartnershipManagerPermission,)

    def get_pdf_filename(self):
        return str(self.pd)

    def get(self, request, *args, **kwargs):
        pd = self.get_pd_or_404(self.kwargs.get("pk"))
        data = {
            "pd": self.get_queryset().get(pk=pd.pk),
        }

        return render_to_pdf_response(request, "pd/detail.html", data)


class PMPInterventionDeleteView(PMPInterventionMixin, InterventionDeleteView):
    """Wrapper for InterventionDeleteView"""


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
        return Intervention.objects.filter(pk=self.kwargs.get('intervention_pk')).first()

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
        return self.get_pd_or_404(self.kwargs.get("intervention_pk"))

    def get_object(self):
        obj, __ = InterventionManagementBudget.objects.get_or_create(
            intervention=self.get_intervention(),
        )
        return obj

    def get_serializer(self, *args, **kwargs):
        if kwargs.get("data"):
            kwargs["data"]["intervention"] = self.kwargs.get("intervention_pk")
        return super().get_serializer(*args, **kwargs)


class PMPInterventionSupplyItemMixin(
        DetailedInterventionResponseMixin,
        PMPInterventionMixin,
):
    queryset = InterventionSupplyItem.objects
    serializer_class = InterventionSupplyItemSerializer

    def get_partner_staff_qs(self, qs):
        return qs.filter(
            intervention__agreement__partner__in=self.partners(),
            intervention__date_sent_to_partner__isnull=False,
        ).distinct()

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            intervention=self.get_pd(self.kwargs.get("intervention_pk")),
        )

    def get_intervention(self) -> Intervention:
        return self.get_pd(self.kwargs.get("intervention_pk"))


class PMPInterventionSupplyItemListCreateView(
        PMPInterventionSupplyItemMixin,
        ListCreateAPIView,
):
    def get_serializer(self, *args, **kwargs):
        if kwargs.get("data"):
            kwargs["data"]["intervention"] = self.get_pd(
                self.kwargs.get("intervention_pk"),
            )
        return super().get_serializer(*args, **kwargs)


class PMPInterventionSupplyItemRetrieveUpdateView(
        PMPInterventionSupplyItemMixin,
        RetrieveUpdateDestroyAPIView,
):
    """View for retrieve/update/destroy of Intervention Supply Item"""


class PMPInterventionSupplyItemUploadView(
        PMPInterventionMixin,
        APIView,
):
    serializer_class = InterventionSupplyItemUploadSerializer

    def post(self, request, *args, **kwargs):
        intervention = self.get_pd_or_404(self.kwargs.get("intervention_pk"))
        serializer = InterventionSupplyItemUploadSerializer(data=request.data)
        # validate csv uploaded file
        if not serializer.is_valid():
            return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

        # processing of file not in validator as we want to extra the data
        # and use in later process
        try:
            file_data = serializer.extract_file_data()
        except ValidationError as err:
            return Response(
                {"supply_items_file": err.detail},
                status.HTTP_400_BAD_REQUEST,
            )

        # update all supply items related to intervention
        for title, unit_number, unit_price in file_data:
            # check if supply item exists
            supply_qs = InterventionSupplyItem.objects.filter(
                intervention=intervention,
                title=title,
                unit_price=unit_price,
            )
            if supply_qs.exists():
                item = supply_qs.get()
                item.unit_number += unit_number
                item.save()
            else:
                InterventionSupplyItem.objects.create(
                    intervention=intervention,
                    title=title,
                    unit_number=unit_number,
                    unit_price=unit_price,
                )
        # make sure we get the correct totals
        intervention.refresh_from_db()
        return Response(
            InterventionDetailSerializer(
                intervention,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )


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
        DetailedInterventionResponseMixin,
        InterventionIndicatorsListView,
):
    def get_intervention(self):
        if not hasattr(self, '_intervention'):
            self._intervention = LowerResult.objects.get(
                pk=self.kwargs.get("lower_result_pk"),
            ).result_link.intervention
        return self._intervention
