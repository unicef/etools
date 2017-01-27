import operator
import functools
import logging

from django.db import transaction
from django.db.models import Q

from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework_csv import renderers as r

from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from partners.models import (
    InterventionBudget,
    Intervention,
    InterventionPlannedVisits,
    InterventionAttachment,
    InterventionAmendment,
    InterventionSectorLocationLink,
    InterventionResultLink
)
from partners.serializers.interventions_v2 import (
    InterventionListSerializer,
    InterventionDetailSerializer,
    InterventionCreateUpdateSerializer,
    InterventionExportSerializer,
    InterventionBudgetCUSerializer,
    PlannedVisitsCUSerializer,
    InterventionAttachmentSerializer,
    InterventionAmendmentCUSerializer,
    InterventionSectorLocationCUSerializer,
    InterventionResultCUSerializer
)
from partners.exports_v2 import InterventionCvsRenderer
from partners.filters import PartnerScopeFilter
from EquiTrack.validation_mixins import ValidatorViewMixin
from partners.validation.interventions import InterventionValid

class InterventionListAPIView(ListCreateAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = InterventionListSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (r.JSONRenderer, InterventionCvsRenderer)

    def get_serializer_class(self):
        """
        Use different serilizers for methods
        """
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") == 'csv':
                    return InterventionExportSerializer
        if self.request.method == "POST":
            return InterventionCreateUpdateSerializer
        return super(InterventionListAPIView, self).get_serializer_class()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Add a new Intervention
        :return: JSON
        """
        planned_budget = request.data.pop("planned_budget", [])
        attachements = request.data.pop("attachments", [])
        planned_visits = request.data.pop("planned_visits", [])
        amendments = request.data.pop("amendments", [])

        # TODO: rename these
        supplies = request.data.pop("supplies", [])
        distributions = request.data.pop("distributions", [])

        intervention_serializer = self.get_serializer(data=request.data)
        intervention_serializer.is_valid(raise_exception=True)
        intervention = intervention_serializer.save()

        # TODO: add planned_budget, planned_visits, attachements, amendments, supplies, distributions

        headers = self.get_success_headers(intervention_serializer.data)
        return Response(
            intervention_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def get_queryset(self, format=None):
        q = Intervention.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []

            if "document_type" in query_params.keys():
                queries.append(Q(partnership_type=query_params.get("document_type")))
            if "country_programme" in query_params.keys():
                queries.append(Q(agreement__country_programme=query_params.get("country_programme")))
            if "sector" in query_params.keys():
                queries.append(Q(sector_locations__sector__id=query_params.get("sector")))
            if "status" in query_params.keys():
                queries.append(Q(status=query_params.get("status")))
            if "unicef_focal_points" in query_params.keys():
                queries.append(Q(unicef_focal_points__in=[query_params.get("unicef_focal_points")]))
            if "start" in query_params.keys():
                queries.append(Q(start__gte=query_params.get("start")))
            if "end" in query_params.keys():
                queries.append(Q(end__lte=query_params.get("end")))
            if "office" in query_params.keys():
                queries.append(Q(offices__in=[query_params.get("office")]))
            if "location" in query_params.keys():
                queries.append(Q(sector_locations__locations__name__icontains=query_params.get("location")))
            if "search" in query_params.keys():
                queries.append(
                    Q(title__icontains=query_params.get("search")) |
                    Q(agreement__partner__name__icontains=query_params.get("search")) |
                    Q(number__icontains=query_params.get("search"))
                )
            if queries:
                expression = functools.reduce(operator.and_, queries)
                q = q.filter(expression)
        return q

    def list(self, request):
        """
        Checks for format query parameter
        :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super(InterventionListAPIView, self).list(request)
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                response['Content-Disposition'] = "attachment;filename=interventions.csv"

        return response


class InterventionDetailAPIView(ValidatorViewMixin, RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update Agreement.
    """
    queryset = Intervention.objects.all()
    serializer_class = InterventionDetailSerializer
    permission_classes = (IsAdminUser,)

    SERIALIZER_MAP = {
        'planned_budget' : InterventionBudgetCUSerializer,
        'planned_visits': PlannedVisitsCUSerializer,
        'attachments': InterventionAttachmentSerializer,
        'amendments': InterventionAmendmentCUSerializer,
        'sector_locations': InterventionSectorLocationCUSerializer
    }

    def get_serializer_class(self):
        """
        Use different serilizers for methods
        """
        if self.request.method == "PUT":
            return InterventionCreateUpdateSerializer
        return super(InterventionDetailAPIView, self).get_serializer_class()

    def retrieve(self, request, pk=None, format=None):
        """
        Returns an Intervention object for this PK
        """
        try:
            queryset = self.queryset.get(id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except Intervention.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = ['planned_budget', 'planned_visits', 'attachments', 'amendments', 'sector_locations']

        instance, old_instance, serializer = self.my_update(request, related_fields, **kwargs)

        validator = InterventionValid(instance, old=old_instance, user=request.user)
        if not validator.is_valid:
            logging.debug(validator.errors)
            raise ValidationError(validator.errors)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()
            serializer = self.get_serializer(instance)

        return Response(serializer.data)
