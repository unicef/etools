from __future__ import absolute_import, division, print_function, unicode_literals

from django_filters.rest_framework import DjangoFilterBackend
from hact.models import HactHistory
from hact.serializers import HactHistoryExportSerializer, HactHistorySerializer
from hact.renderers import HactHistoryCSVRenderer
from rest_framework import views
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework_csv.renderers import JSONRenderer


class HactHistoryAPIView(ListAPIView):
    """
    Returns HACT history.
    """
    permission_classes = (IsAdminUser,)
    queryset = HactHistory.objects.all()
    serializer_class = HactHistorySerializer
    renderer_classes = (JSONRenderer, HactHistoryCSVRenderer)

    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('year', )
    filename = 'hact_history'

    def get_serializer_class(self):
        query_params = self.request.query_params
        if query_params.get("format") == 'csv':
            return HactHistoryExportSerializer
        return super(HactHistoryAPIView, self).get_serializer_class()

    def get_serializer(self, *args, **kwargs):
        if self.request.query_params.get("format") == 'csv':
            return super(HactHistoryAPIView, self).get_serializer(*args, **kwargs)
        return super(HactHistoryAPIView, self).get_serializer(*args, **kwargs)

    def get_renderer_context(self):
        context = super(HactHistoryAPIView, self).get_renderer_context()
        sample_data = self.get_queryset().first()
        context["header"] = [x[0] for x in sample_data.partner_values]
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


class GraphHactView(views.APIView):
    permission_classes = []

    # temporary static json
    def get(self, request, *args, **kwargs):
        return Response(
            {
                'programmatic_visits': {
                    'completed': 15,
                    'min_required': 10,
                },
                'spot_checks': {
                    'completed': 5,
                    'min_required': 13,
                },
                'financial_findings': [
                    {
                        'name': 'Total Audited Expenditure',
                        'value': 34345000,
                        'highlighted': False,
                    },
                    {
                        'name': 'Total Financial Findings',
                        'value': 1239300,
                        'highlighted': True,
                    },
                    {
                        'name': 'Refunds',
                        'value': 345000,
                        'highlighted': False,
                    },
                    {
                        'name': 'Additional Supporting Documentation Received',
                        'value': 235678,
                        'highlighted': False,
                    },
                    {
                        'name': 'Justification Provided and Accepted',
                        'value': 5540,
                        'highlighted': False,
                    },
                    {
                        'name': 'Write-off Recorded',
                        'value': 89567,
                        'highlighted': False,
                    },
                    {
                        'name': 'Outstanding(Requires Follow-up)',
                        'value': 900000,
                        'highlighted': True,
                    }],
                'financial_findings_numbers': [
                    {'name': 'Number of High Priority Findings',
                     'value': 20},
                    {
                        'name': 'Number of Medium Priority Findings',
                        'value': 30,
                    },
                    {
                        'name': 'Number of Low Priority Findings',
                        'value': 45,
                    },
                    {
                        'name': 'Audit Opinion',
                        'value': [
                            {
                                'name': 'qualified',
                                'value': 34,
                            },
                            {
                                'name': 'unqualified',
                                'value': 22,
                            },
                            {'name': 'denial',
                             'value': 10},
                            {'name': 'adverse',
                             'value': 40},
                        ],
                    }],
                'charts': {
                    'cash_transfers_amounts': [
                        ['Risk Rating', 'Not Required', 'Low', 'Medium', 'Significant', 'High', 'Number of IPs'],
                        ['$0-50,0000', 0, 200000, 100000, 30000, 0, 37],
                        ['$50,001-100,0000', 410000, 0, 360000, 120000, 40000, 15],
                        ['$100,001-350,0000', 225000, 515000, 400000, 0, 0, 15],
                        ['$350,001-500,0000', 143000, 35000, 350000, 0, 100000, 5],
                        ['>$500,000', 85000, 66000, 240000, 400000, 20000, 20],
                    ],
                    'cash_transfers_risk_ratings': [
                        ['Risk Rating', 'Total Cash Transfers', {'role': 'style'}, 'Number of IPs'],
                        ['Not Required', 10000, '#D8D8D8', 5],
                        ['Low', 35000, '#2BB0F2', 12],
                        ['Medium', 55000, '#FECC02', 4],
                        ['Significant', 15000, '#F05656', 6],
                        ['High', 3500, '#751010', 4],
                    ],
                    'cash_transfers_partner_type': [
                        ['Partner Type', 'Total Cash Transfers', {'role': 'style'}, 'Number of Partners'],
                        ['CSO', 60000, '#FECC02', 15],
                        ['GOV', 93000, '#F05656', 5],
                    ],
                    'spot_checks_completed': [
                        ['Completed by', 'Count'],
                        ['Staff', 18],
                        ['Service Providers', 8],
                    ],
                },
            }
        )
