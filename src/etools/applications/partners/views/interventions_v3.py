from django.db import transaction
from django.http import Http404

from rest_framework import status
from rest_framework.generics import get_object_or_404, ListCreateAPIView, RetrieveUpdateDestroyAPIView
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
from etools.applications.reports.models import LowerResult


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
            intervention_pk = self.kwargs.get('intervention_pk')
            if intervention_pk is None:
                raise Http404
            self._intervention = get_object_or_404(Intervention.objects, pk=intervention_pk)
        return self._intervention

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['intervention'] = self.get_root_object()
        return context


class InterventionPDOutputsListCreateView(InterventionPDOutputsViewMixin, ListCreateAPIView):
    pass


class InterventionPDOutputsDetailUpdateView(InterventionPDOutputsViewMixin, RetrieveUpdateDestroyAPIView):
    pass
