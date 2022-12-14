import functools
from copy import copy

from django.conf import settings
from django.db import transaction, utils
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _

from easy_pdf.rendering import render_to_pdf_response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import is_success
from rest_framework.views import APIView
from unicef_djangolib.fields import CURRENCY_LIST

from etools.applications.field_monitoring.permissions import IsEditAction, IsReadAction
from etools.applications.partners.exports_v2 import InterventionXLSRenderer
from etools.applications.partners.filters import InterventionEditableByFilter
from etools.applications.partners.models import (
    Intervention,
    InterventionAttachment,
    InterventionManagementBudget,
    InterventionReview,
    InterventionReviewNotification,
    InterventionRisk,
    InterventionSupplyItem,
    PRCOfficerInterventionReview,
)
from etools.applications.partners.permissions import (
    AmendmentSessionOnlyDeletePermission,
    intervention_field_is_editable_permission,
    PMPInterventionPermission,
    UserBelongsToObjectPermission,
    UserIsStaffPermission,
)
from etools.applications.partners.serializers.exports.interventions import (
    InterventionExportFlatSerializer,
    InterventionExportSerializer,
)
from etools.applications.partners.serializers.interventions_v2 import (
    InterventionBudgetCUSerializer,
    InterventionCreateUpdateSerializer,
    MinimalInterventionListSerializer,
)
from etools.applications.partners.serializers.interventions_v3 import (
    InterventionDetailResultsStructureSerializer,
    InterventionDetailSerializer,
    InterventionListSerializer,
    InterventionManagementBudgetSerializer,
    InterventionRiskSerializer,
    InterventionSupplyItemSerializer,
    InterventionSupplyItemUploadSerializer,
    PMPInterventionAttachmentSerializer,
)
from etools.applications.partners.serializers.v3 import (
    InterventionReviewSerializer,
    PartnerInterventionLowerResultSerializer,
    PRCOfficerInterventionReviewSerializer,
    UNICEFInterventionLowerResultSerializer,
)
from etools.applications.partners.validation.interventions import InterventionValid
from etools.applications.partners.views.intervention_snapshot import FullInterventionSnapshotDeleteMixin
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
from etools.libraries.djangolib.utils import get_current_site


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

    def get_intervention(self):
        raise NotImplementedError

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if request.method.lower() in self.detailed_intervention_methods and is_success(response.status_code):
            response.data['intervention'] = self.detailed_intervention_serializer(
                instance=self.get_intervention(),
                context=self.get_serializer_context(),
            ).data
        return response


class InterventionAutoTransitionsMixin:
    @staticmethod
    def perform_auto_transitions(intervention, user):
        validator = InterventionValid(intervention, old=intervention, user=user, disable_rigid_check=True)
        validator.total_validation


class PMPInterventionListCreateView(PMPInterventionMixin, InterventionListAPIView):
    permission_classes = (IsAuthenticated, PMPInterventionPermission)
    search_terms = (
        'title__icontains',
        'agreement__partner__organization__name__icontains',
        'number__icontains',
        'cfei_number__icontains',
    )
    filter_backends = InterventionListAPIView.filter_backends + (
        InterventionEditableByFilter,
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
        planned_budget = request.data.get("planned_budget")
        super().create(request, *args, **kwargs)

        # check if setting currency
        if planned_budget and planned_budget.get("currency"):
            currency = planned_budget.get("currency")
            if currency not in CURRENCY_LIST:
                raise ValidationError(f"Invalid currency: {currency}.")
            self.instance.planned_budget.currency = currency
            self.instance.planned_budget.save()

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


class PMPInterventionRetrieveResultsStructure(PMPInterventionMixin, RetrieveAPIView):
    queryset = Intervention.objects.detail_qs()
    serializer_class = InterventionDetailResultsStructureSerializer
    permission_classes = (IsAuthenticated, PMPInterventionPermission,)


class PMPInterventionPDFView(PMPInterventionMixin, RetrieveAPIView):
    queryset = Intervention.objects.detail_qs().all()
    permission_classes = (IsAuthenticated, PMPInterventionPermission,)

    def get(self, request, *args, **kwargs):
        pd = self.get_pd_or_404(self.kwargs.get("pk"))
        # re-fetch to get prefetched detail queries
        pd = self.get_queryset().get(pk=pd.pk)
        font_path = settings.PACKAGE_ROOT + '/assets/fonts/'

        data = {
            "domain": 'https://{}'.format(get_current_site().domain),
            "pd": pd,
            "pd_offices": [o.name for o in pd.offices.all()],
            "pd_locations": [location.name for location in pd.flat_locations.all()],
            "font_path": font_path,
        }

        return render_to_pdf_response(request, "pd/detail.html", data, filename=f'{str(pd)}.pdf')


class PMPInterventionXLSView(PMPInterventionMixin, RetrieveAPIView):
    queryset = Intervention.objects.detail_qs().all()
    permission_classes = (IsAuthenticated, PMPInterventionPermission,)

    def get(self, request, *args, **kwargs):
        pd = self.get_pd_or_404(self.kwargs.get("pk"))
        pd = self.get_queryset().get(pk=pd.pk)

        return HttpResponse(content=InterventionXLSRenderer(pd).render(), headers={
            'Content-Disposition': 'attachment;filename={}.xlsx'.format(str(pd))
        })


class PMPInterventionDeleteView(PMPInterventionMixin, InterventionDeleteView):
    """Wrapper for InterventionDeleteView"""


class InterventionPDOutputsViewMixin(DetailedInterventionResponseMixin):
    queryset = LowerResult.objects.select_related('result_link').order_by('id')
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('pd_outputs')),
        AmendmentSessionOnlyDeletePermission,
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


class InterventionPDOutputsDetailUpdateView(
    InterventionPDOutputsViewMixin,
    FullInterventionSnapshotDeleteMixin,
    RetrieveUpdateDestroyAPIView,
):
    def perform_destroy(self, instance):
        # do cleanup if pd output is still not associated to cp output
        result_link = instance.result_link
        instance.delete()
        if result_link.cp_output is None and not result_link.ll_results.exists():
            result_link.delete()


class PMPInterventionManagementBudgetRetrieveUpdateView(
    DetailedInterventionResponseMixin, PMPInterventionMixin, RetrieveUpdateAPIView
):
    queryset = InterventionManagementBudget.objects.prefetch_related('items')
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


class PMPReviewMixin(DetailedInterventionResponseMixin, PMPBaseViewMixin):
    queryset = InterventionReview.objects.all()
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('reviews'))
    ]
    serializer_class = InterventionReviewSerializer

    def get_root_object(self):
        return Intervention.objects.get(pk=self.kwargs["intervention_pk"])

    def get_intervention(self):
        return self.get_root_object()

    def get_queryset(self):
        qs = super().get_queryset().filter(
            intervention__pk=self.kwargs["intervention_pk"],
        )
        if self.is_partner_staff():
            return qs.none()
        return qs

    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs:
            kwargs["data"]["intervention"] = self.get_root_object().pk
        return super().get_serializer(*args, **kwargs)


class PMPReviewView(PMPReviewMixin, ListAPIView):
    lookup_url_kwarg = "intervention_pk"
    lookup_field = "intervention_id"


class PMPReviewDetailView(PMPReviewMixin, RetrieveUpdateAPIView):
    pass


class PMPReviewNotifyView(PMPReviewMixin, GenericAPIView):
    def post(self, request, *args, **kwargs):
        review = self.get_object()
        if not review.meeting_date:
            return Response([_('Meeting date is not available.')], status=status.HTTP_400_BAD_REQUEST)

        InterventionReviewNotification.notify_officers_for_review(review)
        return Response({})


class PMPOfficerReviewBaseView(DetailedInterventionResponseMixin, PMPBaseViewMixin):
    queryset = PRCOfficerInterventionReview.objects.prefetch_related('user').all()
    serializer_class = PRCOfficerInterventionReviewSerializer

    def get_root_object(self):
        return Intervention.objects.get(pk=self.kwargs['intervention_pk'])

    def get_intervention(self):
        return self.get_root_object()

    def get_queryset(self):
        qs = super().get_queryset().filter(
            overall_review_id=self.kwargs['review_pk'],
            overall_review__intervention_id=self.kwargs['intervention_pk'],
        )
        if self.is_partner_staff():
            return qs.none()
        return qs


class PMPOfficerReviewListView(PMPOfficerReviewBaseView, ListAPIView):
    permission_classes = [IsAuthenticated, UserIsStaffPermission]


class PMPOfficerReviewDetailView(PMPOfficerReviewBaseView, UpdateAPIView):
    permission_classes = [
        IsAuthenticated,
        UserIsStaffPermission,
        intervention_field_is_editable_permission('prc_reviews'),
        UserBelongsToObjectPermission,
    ]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_pk'


class PMPInterventionSupplyItemMixin(
        DetailedInterventionResponseMixin,
        PMPInterventionMixin,
):
    queryset = InterventionSupplyItem.objects
    serializer_class = InterventionSupplyItemSerializer
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('supply_items'))
    ]

    def get_partner_staff_qs(self, qs):
        return qs.filter(
            intervention__agreement__partner__in=self.partners(),
            intervention__date_sent_to_partner__isnull=False,
        ).distinct()

    def get_queryset(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        return qs.filter(
            intervention=self.get_pd(self.kwargs.get("intervention_pk")),
        )

    def get_intervention(self):
        return self.get_pd(self.kwargs.get("intervention_pk"))

    def get_root_object(self):
        return self.get_intervention()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['intervention'] = self.get_intervention()
        return context


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
        for title, unit_number, unit_price, product_number in file_data:
            # check if supply item exists
            supply_qs = InterventionSupplyItem.objects.filter(
                intervention=intervention,
                title=title,
                unit_price=unit_price,
                provided_by=InterventionSupplyItem.PROVIDED_BY_UNICEF,
            )
            if supply_qs.exists():
                item = supply_qs.get()
                item.unit_number += unit_number
                item.save()
            else:
                try:
                    InterventionSupplyItem.objects.create(
                        intervention=intervention,
                        title=title,
                        unit_number=unit_number,
                        unit_price=unit_price,
                        unicef_product_number=product_number,
                        provided_by=InterventionSupplyItem.PROVIDED_BY_UNICEF,
                    )
                except utils.DataError as err:
                    return Response(
                        {"supply_items_file": f"{product_number}:  {str(err)}"},
                        status.HTTP_400_BAD_REQUEST,
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
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('pd_outputs')),
        AmendmentSessionOnlyDeletePermission,
    ]
    serializer_class = InterventionActivityDetailSerializer

    def get_root_object(self):
        return Intervention.objects.filter(
            pk=self.kwargs.get('intervention_pk'),
        ).first()

    def get_intervention(self):
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


class InterventionRiskDeleteView(FullInterventionSnapshotDeleteMixin, DestroyAPIView):
    queryset = InterventionRisk.objects
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('risks'))
    ]

    @functools.cache
    def get_root_object(self):
        return Intervention.objects.filter(pk=self.kwargs.get('intervention_pk')).first()

    def get_intervention(self):
        return self.get_root_object()

    def get_queryset(self):
        return super().get_queryset().filter(intervention=self.get_root_object())


class PMPInterventionAttachmentListCreateView(
    InterventionAutoTransitionsMixin,
    DetailedInterventionResponseMixin,
    ListCreateAPIView,
):
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

    @transaction.atomic
    def perform_create(self, serializer):
        intervention = self.get_root_object()
        serializer.save(intervention=intervention)
        self.perform_auto_transitions(intervention, self.request.user)

    def get_intervention(self):
        return self.get_root_object()


class PMPInterventionAttachmentUpdateDeleteView(
    InterventionAutoTransitionsMixin,
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

    def get_intervention(self):
        return self.get_root_object()

    @transaction.atomic
    def perform_update(self, serializer):
        super().perform_update(serializer)
        self.perform_auto_transitions(self.get_root_object(), self.request.user)


class PMPInterventionIndicatorsUpdateView(
        DetailedInterventionResponseMixin,
        InterventionIndicatorsUpdateView,
):
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('result_links')),
    ]

    def get_root_object(self):
        if not hasattr(self, '_intervention'):
            self._intervention = self.get_object().lower_result.result_link.intervention
        return self._intervention

    def get_intervention(self):
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
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('result_links')),
    ]

    def get_intervention(self):
        if not hasattr(self, '_intervention'):
            self._intervention = LowerResult.objects.get(
                pk=self.kwargs.get("lower_result_pk"),
            ).result_link.intervention
        return self._intervention

    def get_root_object(self):
        return self.get_intervention()
