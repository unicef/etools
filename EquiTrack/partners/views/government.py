import operator
import functools
import logging

from django.db import transaction
from django.db.models import Q

from rest_framework.permissions import IsAdminUser
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework_csv import renderers as r

from EquiTrack.validation_mixins import ValidatorViewMixin

from partners.models import GovernmentIntervention
from partners.serializers.government import (
    GovernmentInterventionListSerializer,
    GovernmentInterventionCreateUpdateSerializer,
    GovernmentInterventionExportSerializer,
    GovernmentInterventionResultNestedSerializer
)
from partners.filters import PartnerScopeFilter


class GovernmentInterventionListAPIView(ListCreateAPIView, ValidatorViewMixin):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    serializer_class = GovernmentInterventionListSerializer
    permission_classes = (IsAdminUser,)
    filter_backends = (PartnerScopeFilter,)
    renderer_classes = (r.JSONRenderer, r.CSVRenderer)

    SERIALIZER_MAP = {
        'results': GovernmentInterventionResultNestedSerializer
    }

    def get_serializer_class(self):
        """
        Use different serilizers for methods
        """
        if self.request.method == "GET":
            query_params = self.request.query_params
            if "format" in query_params.keys():
                if query_params.get("format") == 'csv':
                    return GovernmentInterventionExportSerializer
        if self.request.method == "POST":
            return GovernmentInterventionCreateUpdateSerializer
        return super(GovernmentInterventionListAPIView, self).get_serializer_class()

    @transaction.atomic
    def create(self, request, *args, **kwargs):

        related_fields = ['results']

        serializer = self.my_create(request, related_fields, snapshot=True, **kwargs)

        #TOOD: split out related fields and get them validated through the proper serializers
        #(use the validator)

        return Response(serializer.data)

    def get_queryset(self, format=None):
        q = GovernmentIntervention.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []

            if "partner" in query_params.keys():
                queries.append(Q(partner__id=query_params.get("partner")))
            if "country_programme" in query_params.keys():
                queries.append(Q(country_programme=query_params.get("country_programme")))
            if "sector" in query_params.keys():
                queries.append(Q(results__sectors=query_params.get("sector")))
            if "year" in query_params.keys():
                queries.append(Q(results__year=query_params.get("sector")))
            if "unicef_focal_point" in query_params.keys():
                queries.append(Q(results__unicef_managers=query_params.get("sector")))

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
        response = super(GovernmentInterventionListAPIView, self).list(request)
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                response['Content-Disposition'] = "attachment;filename=interventions.csv"

        return response


class GovernmentDetailAPIView(ValidatorViewMixin, RetrieveUpdateDestroyAPIView):
    """
    Retrieve and Update Agreement.
    """
    queryset = GovernmentIntervention.objects.all()
    serializer_class = GovernmentInterventionCreateUpdateSerializer
    permission_classes = (IsAdminUser,)

    SERIALIZER_MAP = {
        'results': GovernmentInterventionResultNestedSerializer
    }

    def retrieve(self, request, pk=None, format=None):
        """
        Returns an Intervention object for this PK
        """
        try:
            queryset = self.queryset.get(id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except GovernmentIntervention.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        related_fields = ['results']

        instance, old_instance, serializer = self.my_update(request, related_fields, snapshot=True **kwargs)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()
            serializer = self.get_serializer(instance)

        return Response(serializer.data)
