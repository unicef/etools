from django.db import transaction

from rest_framework import status
from rest_framework.generics import CreateAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from etools.applications.field_monitoring.permissions import IsEditAction, IsReadAction
from etools.applications.partners.models import Intervention
from etools.applications.partners.permissions import intervention_field_is_editable_permission
from etools.applications.partners.serializers.v3 import (
    PartnerInterventionLowerResultSerializer,
    UNICEFInterventionLowerResultSerializer,
)
from etools.applications.partners.views.interventions_v2 import InterventionDetailAPIView, InterventionListAPIView
from etools.applications.partners.views.v3 import PMPBaseViewMixin
from etools.applications.reports.models import InterventionActivity, LowerResult
from etools.applications.reports.serializers.v2 import InterventionActivityDetailSerializer


class PMPInterventionMixin(PMPBaseViewMixin):
    def get_queryset(self, format=None):
        qs = super().get_queryset()
        # if partner, limit to interventions that they are associated with
        if self.is_partner_staff():
            qs = qs.filter(agreement__partner__in=self.partners())
        return qs


class PMPInterventionListCreateView(PMPInterventionMixin, InterventionListAPIView):
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


class InterventionPDOutputsViewMixin:
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

    def get_serializer(self, *args, **kwargs):
        kwargs['intervention'] = self.get_root_object()
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(result_link__intervention=self.get_root_object())


class InterventionPDOutputsListCreateView(InterventionPDOutputsViewMixin, ListCreateAPIView):
    pass


class InterventionPDOutputsDetailUpdateView(InterventionPDOutputsViewMixin, RetrieveUpdateDestroyAPIView):
    pass


class InterventionActivityViewMixin():
    queryset = InterventionActivity.objects.prefetch_related('items', 'time_frames').order_by('id')
    permission_classes = [
        IsAuthenticated,
        IsReadAction | (IsEditAction & intervention_field_is_editable_permission('pd_outputs'))
    ]
    serializer_class = InterventionActivityDetailSerializer

    def get_root_object(self):
        if not hasattr(self, '_intervention'):
            self._intervention = Intervention.objects.filter(pk=self.kwargs.get('intervention_pk')).first()
        return self._intervention

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
