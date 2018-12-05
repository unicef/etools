
import json

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework_csv.renderers import JSONRenderer
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.hact.models import AggregateHact, HactHistory
from etools.applications.hact.renderers import HactHistoryCSVRenderer
from etools.applications.hact.serializers import (AggregateHactSerializer,
                                                  HactHistoryExportSerializer, HactHistorySerializer,)


class HactHistoryAPIView(QueryStringFilterMixin, ListAPIView):
    """
    Returns HACT history.
    """
    permission_classes = (IsAdminUser,)
    queryset = HactHistory.objects.all()
    serializer_class = HactHistorySerializer
    renderer_classes = (JSONRenderer, HactHistoryCSVRenderer)
    filename = 'hact_history'
    filters = (
        ('year', 'year'),
    )

    def get_serializer_class(self):
        query_params = self.request.query_params
        if query_params.get("format") == 'csv':
            return HactHistoryExportSerializer
        return super(HactHistoryAPIView, self).get_serializer_class()

    def get_renderer_context(self):
        context = super(HactHistoryAPIView, self).get_renderer_context()
        data = self.get_queryset().first().partner_values
        try:
            data = json.loads(data)
        except (ValueError, TypeError):
            pass
        context["header"] = [x[0] for x in data]
        return context

    def list(self, request, format=None):
        """
        Checks for format query parameter
        :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super(HactHistoryAPIView, self).list(request)
        if query_params.get("format") == 'csv':
            response['Content-Disposition'] = "attachment;filename={}.csv".format(self.filename)
        return response


class GraphHactView(RetrieveAPIView):
    permission_classes = []

    lookup_field = 'year'
    queryset = AggregateHact.objects.all()
    serializer_class = AggregateHactSerializer
