import operator
import functools

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

from partners.filters import PartnerScopeFilter


class InterventionListAPIView(ListCreateAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = InterventionListSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (r.JSONRenderer, r.CSVRenderer)

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

            # TODO: update these filters
            if "partnership_type" in query_params.keys():
                queries.append(Q(partnership_type=query_params.get("partnership_type")))
            if "country_programme" in query_params.keys():
                queries.append(Q(country_programme=query_params.get("country_programme")))
            if "sector" in query_params.keys():
                queries.append(Q(pcasectors__sector=query_params.get("sector")))
            if "status" in query_params.keys():
                queries.append(Q(status=query_params.get("status")))
            if "unicef_managers" in query_params.keys():
                queries.append(Q(unicef_managers__in=[query_params.get("unicef_managers")]))
            if "start_date" in query_params.keys():
                queries.append(Q(start_date__gte=query_params.get("start_date")))
            if "end_date" in query_params.keys():
                queries.append(Q(end_date__lte=query_params.get("end_date")))
            if "office" in query_params.keys():
                queries.append(Q(office__in=[query_params.get("office")]))
            if "location" in query_params.keys():
                queries.append(Q(locations__location=query_params.get("location")))
            if "search" in query_params.keys():
                queries.append(
                    Q(title__icontains=query_params.get("search")) |
                    Q(partner__name__icontains=query_params.get("search"))
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


class InterventionDetailAPIView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update Agreement.
    """
    queryset = Intervention.objects.all()
    serializer_class = InterventionDetailSerializer
    permission_classes = (IsAdminUser,)

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

    def up_related_field(self, mother_obj, field, fieldClass, fieldSerializer, rel_prop_name, reverse_name, partial=False):
        if not field:
            return
        for item in field:
            item.update({reverse_name: mother_obj.pk})
            if item.get('id', None):
                try:
                    instance = fieldClass.objects.get(id=item['id'])
                except fieldClass.DoesNotExist:
                    instance = None

                instance_serializer = fieldSerializer(instance=instance,
                                                      data=item,
                                                      partial=partial)
            else:
                instance_serializer = fieldSerializer(data=item)

            try:
                instance_serializer.is_valid(raise_exception=True)
            except ValidationError as e:
                e.detail = {rel_prop_name: e.detail}
                raise e
            instance_serializer.save()

    @transaction.atomic
    def update(self, request, *args, **kwargs):

        partial = kwargs.pop('partial', False)
        planned_budget = request.data.pop("planned_budget", [])
        attachements = request.data.pop("attachments", [])
        planned_visits = request.data.pop("planned_visits", [])
        amendments = request.data.pop("amendments", [])
        sector_locations = request.data.pop("sector_locations", [])
        instance = self.get_object()

        # TODO: rename these
        supplies = request.data.pop("supplies", [])
        distributions = request.data.pop("distributions", [])


        result_links = request.data.pop("result_links", [])

        intervention_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        intervention_serializer.is_valid(raise_exception=True)
        intervention = intervention_serializer.save()

        # TODO: test attachements, amendments, supplies, distributions
        self.up_related_field(intervention, planned_budget,
                              InterventionBudget, InterventionBudgetCUSerializer,
                              'planned_budget', 'intervention', partial)
        self.up_related_field(intervention, planned_visits,
                              InterventionPlannedVisits, PlannedVisitsCUSerializer,
                              'planned_visits', 'intervention', partial)
        self.up_related_field(intervention, attachements,
                              InterventionAttachment, InterventionAttachmentSerializer,
                              'attachments', 'intervention', partial)
        self.up_related_field(intervention, amendments,
                              InterventionAmendment, InterventionAmendmentCUSerializer,
                              'amendments', 'intervention', partial)
        self.up_related_field(intervention, sector_locations,
                              InterventionSectorLocationLink, InterventionSectorLocationCUSerializer,
                              'sector_locations', 'intervention', partial)
        # self.up_related_field(intervention, result_links,
        #                       InterventionResultLink, InterventionResultCUSerializer,
        #                       'sector_locations', 'intervention', partial)


        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()
            intervention_serializer = self.get_serializer(instance)

        return Response(intervention_serializer.data)