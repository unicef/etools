from csv import DictWriter

from django.http import HttpResponse
from django.views.generic import DetailView

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework_csv.renderers import JSONRenderer
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.hact.models import AggregateHact, HactHistory
from etools.applications.hact.renderers import HactHistoryCSVRenderer
from etools.applications.hact.serializers import (
    AggregateHactSerializer,
    HactHistoryExportSerializer,
    HactHistorySerializer,
)


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
        return super().get_serializer_class()

    def get_renderer_context(self):
        context = super().get_renderer_context()
        data = {}
        if self.get_queryset().exists():
            data = self.get_queryset().first().partner_values
        context["header"] = [x[0] for x in data]
        return context

    def list(self, request):
        """
        Checks for format query parameter
        :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super().list(request)
        if query_params.get("format") == 'csv':
            response['Content-Disposition'] = "attachment;filename={}.csv".format(self.filename)
        return response


class GraphHactView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    lookup_field = 'year'
    queryset = AggregateHact.objects.all()
    serializer_class = AggregateHactSerializer


class GraphHactExportView(DetailView):
    model = AggregateHact
    slug_field = slug_url_kwarg = 'year'
    fieldnames = ['Label', 'Column', 'Value']
    filename = 'hact_dashboard'

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.filename}.csv"'
        partner_values = self.get_object().partner_values
        export_values = (
            ('Assessment and Assurance Activities', 'Programmatic Visits: Completed',
             partner_values['assurance_activities']['programmatic_visits']['completed']),
            ('Assessment and Assurance Activities', 'Programmatic Visits: Minimum Required',
             partner_values['assurance_activities']['programmatic_visits']['min_required']),
            ('Assessment and Assurance Activities', 'Spot Checks: Completed',
             partner_values['assurance_activities']['spot_checks']['completed']),
            ('Assessment and Assurance Activities', 'Spot Checks: Required',
             partner_values['assurance_activities']['spot_checks']['required']),
            ('Assessment and Assurance Activities', 'Micro Assessments: Completed',
             partner_values['assurance_activities']['micro_assessment']),
            ('Assessment and Assurance Activities', 'Micro Assessments: Expiring',
             partner_values['assurance_activities']['missing_micro_assessment']),
            ('Assessment and Assurance Activities', 'Scheduled Audits',
             partner_values['assurance_activities']['scheduled_audit']),
            ('Assessment and Assurance Activities', 'Special Audits',
             partner_values['assurance_activities']['special_audit']),

            ('Assurance Coverage', 'Coverage by number of IPs: Without Assurance',
                partner_values['assurance_coverage']['coverage_by_number_of_ips'][1][1]),
            ('Assurance Coverage', 'Coverage by number of IPs: Partially Met Requirements',
                partner_values['assurance_coverage']['coverage_by_number_of_ips'][2][1]),
            ('Assurance Coverage', 'Coverage by number of IPs: Met Requirements',
                partner_values['assurance_coverage']['coverage_by_number_of_ips'][3][1]),
            ('Assurance Coverage', 'Coverage by Cash Transfer (USD) (Total): Without Assurance',
                partner_values['assurance_coverage']['coverage_by_cash_transfer'][1][1]),
            ('Assurance Coverage', 'Coverage by Cash Transfer (USD) (Total): Partially Met Requirements',
                partner_values['assurance_coverage']['coverage_by_cash_transfer'][2][1]),
            ('Assurance Coverage', 'Coverage by Cash Transfer (USD) (Total): Met Requirements',
                partner_values['assurance_coverage']['coverage_by_cash_transfer'][3][1]),
            ('Assurance Coverage', 'IP Without Assurance: Programmatic Visits',
             partner_values['assurance_coverage']['table'][0]['value']),
            ('Assurance Coverage', 'IP Without Assurance: Spot Checks',
             partner_values['assurance_coverage']['table'][1]['value']),
            ('Assurance Coverage', 'IP Without Assurance: Both',
             partner_values['assurance_coverage']['table'][2]['value']),

            ('Financial Findings', 'Total Audited Expenditure', partner_values['financial_findings'][0]['value']),
            ('Financial Findings', 'Total Financial Findings', partner_values['financial_findings'][1]['value']),
            ('Financial Findings', 'Refunds', partner_values['financial_findings'][2]['value']),
            ('Financial Findings', 'Additional Supporting Documentation Received',
                partner_values['financial_findings'][3]['value']),
            ('Financial Findings', 'Justification Provided and Accepted',
             partner_values['financial_findings'][4]['value']),
            ('Financial Findings', 'Impairment', partner_values['financial_findings'][5]['value']),
            ('Financial Findings', 'Outstanding (Requires Follow-up)',
             partner_values['financial_findings'][6]['value']),
            ('Financial Findings', 'Number of High Priority Findings',
             partner_values['financial_findings_numbers'][0]['value']),
            ('Financial Findings', 'Number of Medium Priority Findings',
             partner_values['financial_findings_numbers'][1]['value']),
            ('Financial Findings', 'Number of Low Priority Findings',
             partner_values['financial_findings_numbers'][2]['value']),
            ('Financial Findings', 'Audit Opinion: Qualified',
             partner_values['financial_findings_numbers'][3]['value'][0]['value']),
            ('Financial Findings', 'Audit Opinion: Unqualified',
             partner_values['financial_findings_numbers'][3]['value'][1]['value']),
            ('Financial Findings', 'Audit Opinion: Denial',
             partner_values['financial_findings_numbers'][3]['value'][2]['value']),
            ('Financial Findings', 'Audit Opinion: Adverse',
             partner_values['financial_findings_numbers'][3]['value'][3]['value']),

            ('Total Cash Transfer by Cash Transfer Ranges', 'Not Required $0-50,000',
                partner_values['charts']['cash_transfers_amounts'][1][1]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Not Required $50,001-100,000',
                partner_values['charts']['cash_transfers_amounts'][2][1]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Not Required $100,001-350,000',
                partner_values['charts']['cash_transfers_amounts'][3][1]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Not Required $350,001-500,000',
                partner_values['charts']['cash_transfers_amounts'][4][1]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Not Required >$500,000',
                partner_values['charts']['cash_transfers_amounts'][5][1]),

            ('Total Cash Transfer by Cash Transfer Ranges', 'Low $0-50,000',
                partner_values['charts']['cash_transfers_amounts'][1][2]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Low $50,001-100,000',
                partner_values['charts']['cash_transfers_amounts'][2][2]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Low $100,001-350,000',
                partner_values['charts']['cash_transfers_amounts'][3][2]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Low $350,001-500,000',
                partner_values['charts']['cash_transfers_amounts'][4][2]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Low >$500,000',
                partner_values['charts']['cash_transfers_amounts'][5][2]),

            ('Total Cash Transfer by Cash Transfer Ranges', 'Medium $0-50,000',
                partner_values['charts']['cash_transfers_amounts'][1][3]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Medium $50,001-100,000',
                partner_values['charts']['cash_transfers_amounts'][2][3]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Medium $100,001-350,000',
                partner_values['charts']['cash_transfers_amounts'][3][3]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Medium $350,001-500,000',
                partner_values['charts']['cash_transfers_amounts'][4][3]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Medium >$500,000',
                partner_values['charts']['cash_transfers_amounts'][5][3]),

            ('Total Cash Transfer by Cash Transfer Ranges', 'Significant $0-50,000',
                partner_values['charts']['cash_transfers_amounts'][1][4]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Significant $50,001-100,000',
                partner_values['charts']['cash_transfers_amounts'][2][4]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Significant $100,001-350,000',
                partner_values['charts']['cash_transfers_amounts'][3][4]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Significant $350,001-500,000',
                partner_values['charts']['cash_transfers_amounts'][4][4]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Significant >$500,000',
                partner_values['charts']['cash_transfers_amounts'][5][4]),

            ('Total Cash Transfer by Cash Transfer Ranges', 'High $0-50,000',
                partner_values['charts']['cash_transfers_amounts'][1][5]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'High $50,001-100,000',
                partner_values['charts']['cash_transfers_amounts'][2][5]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'High $100,001-350,000',
                partner_values['charts']['cash_transfers_amounts'][3][5]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'High $350,001-500,000',
                partner_values['charts']['cash_transfers_amounts'][4][5]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'High >$500,000',
                partner_values['charts']['cash_transfers_amounts'][5][5]),

            ('Total Cash Transfer by Cash Transfer Ranges', 'Number of IPs $0-50,000',
                partner_values['charts']['cash_transfers_amounts'][1][6]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Number of IPs $50,001-100,000',
                partner_values['charts']['cash_transfers_amounts'][2][6]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Number of IPs $100,001-350,000',
                partner_values['charts']['cash_transfers_amounts'][3][6]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Number of IPs $350,001-500,000',
                partner_values['charts']['cash_transfers_amounts'][4][6]),
            ('Total Cash Transfer by Cash Transfer Ranges', 'Number of IPs >$500,000',
                partner_values['charts']['cash_transfers_amounts'][5][6]),



            ('Total Cash Transfers by IP Risk Rating', 'Not Required Total Cash Transfers',
                partner_values['charts']['cash_transfers_risk_ratings'][1][1]),
            ('Total Cash Transfers by IP Risk Rating', 'Not Required Number of IPs',
                partner_values['charts']['cash_transfers_risk_ratings'][1][3]),

            ('Total Cash Transfers by IP Risk Rating', 'Low Total Cash Transfers',
                partner_values['charts']['cash_transfers_risk_ratings'][2][1]),
            ('Total Cash Transfers by IP Risk Rating', 'Low Required Number of IPs',
                partner_values['charts']['cash_transfers_risk_ratings'][2][3]),

            ('Total Cash Transfers by IP Risk Rating', 'Medium Total Cash Transfers',
                partner_values['charts']['cash_transfers_risk_ratings'][3][1]),
            ('Total Cash Transfers by IP Risk Rating', 'Medium Not Required Number of IPs',
                partner_values['charts']['cash_transfers_risk_ratings'][3][3]),

            ('Total Cash Transfers by IP Risk Rating', 'Significant Total Cash Transfers',
                partner_values['charts']['cash_transfers_risk_ratings'][4][1]),
            ('Total Cash Transfers by IP Risk Rating', 'Significant Not Required Number of IPs',
                partner_values['charts']['cash_transfers_risk_ratings'][4][3]),

            ('Total Cash Transfers by IP Risk Rating', 'High Total Cash Transfers',
                partner_values['charts']['cash_transfers_risk_ratings'][5][1]),
            ('Total Cash Transfers by IP Risk Rating', 'High Not Required Number of IPs',
                partner_values['charts']['cash_transfers_risk_ratings'][5][3]),

            ('Cash Transfers by Partner Type', 'CSO Total Cash Transfers',
                partner_values['charts']['cash_transfers_partner_type'][1][1]),
            ('Cash Transfers by Partner Type', 'CSO Number of Partners',
                partner_values['charts']['cash_transfers_partner_type'][1][3]),
            ('Cash Transfers by Partner Type', 'GOV Total Cash Transfers',
                partner_values['charts']['cash_transfers_partner_type'][2][1]),
            ('Cash Transfers by Partner Type', 'GOV Number of Partners',
                partner_values['charts']['cash_transfers_partner_type'][2][3]),

            ('Spot Checks Completed', 'Staff', partner_values['charts']['spot_checks_completed'][1][1]),
            ('Spot Checks Completed', 'Service Providers', partner_values['charts']['spot_checks_completed'][2][1]),

        )

        writer = DictWriter(response, self.fieldnames)
        writer.writeheader()
        for label, key, value in export_values:
            writer.writerow({'Label': label, 'Column': key, 'Value': value})

        return response
