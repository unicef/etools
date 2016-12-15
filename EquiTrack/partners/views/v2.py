import operator
import functools

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework_csv import renderers as r
from rest_framework.generics import (
    ListCreateAPIView,
    ListAPIView,
    RetrieveUpdateDestroyAPIView,
)
from django.http import HttpResponse, StreamingHttpResponse

from partners.models import PartnerOrganization, Intervention
from partners.permissions import PartnerPermission
from partners.serializers.v1 import PartnerOrganizationSerializer, InterventionSerializer
from partners.serializers.v2 import (
    InterventionListSerializer,
    InterventionDetailSerializer,
    InterventionCreateUpdateSerializer,
    InterventionExportSerializer
)
from partners.filters import PartnerScopeFilter


class InterventionListAPIView(ListCreateAPIView):
    """
    Create new Interventions.
    Returns a list of Interventions.
    """
    queryset = Intervention.objects.all()
    serializer_class = InterventionListSerializer
    permission_classes = (PartnerPermission,)
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

    def create(self, request, *args, **kwargs):
        """
        Add a new Intervention
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.instance = serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def get_queryset(self, format=None):
        q = Intervention.objects.all()
        query_params = self.request.query_params

        if query_params:
            queries = []

            if "partnership_type" in query_params.keys():
                queries.append(Q(partnership_type=query_params.get("partnership_type")))
            # TODO whats this?
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
    permission_classes = (PartnerPermission,)

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


class PartnerInterventionListAPIView(ListAPIView):
    queryset = Intervention.objects.all()
    serializer_class = InterventionSerializer
    permission_classes = (PartnerPermission,)

    def list(self, request, pk=None, format=None):
        """
        Return All Interventions for Partner
        """
        interventions = Intervention.objects.filter(partner_id=pk)
        serializer = InterventionSerializer(interventions, many=True)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
