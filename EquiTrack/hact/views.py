from __future__ import absolute_import, division, print_function, unicode_literals

import json
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from django_filters.rest_framework import DjangoFilterBackend
from hact.models import HactHistory
from hact.renderers import HactHistoryCSVRenderer
from hact.serializers import HactHistoryExportSerializer, HactHistorySerializer
from rest_framework import views
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework_csv.renderers import JSONRenderer

from audit.models import Audit, Engagement, MicroAssessment, SpecialAudit, SpotCheck
from partners.models import PartnerOrganization, PartnerType


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


class GraphHactView(views.APIView):
    permission_classes = []

    def get_queryset(self):
        return PartnerOrganization.objects.all()

    def _sum_json_values(self, filters, filter_dict={}):
        partners = self.get_queryset().filter(**filter_dict)

        def get_value(obj, filters):
            filters = filters.split('__')
            json_field_name = filters.pop(0)
            json_field = getattr(obj, json_field_name)
            for filter in filters:
                json_field = json_field[filter]
            return json_field

        return sum([get_value(p, filters) for p in partners])

    def cash_transfers_amounts(self):
        FIRST_LEVEL = Decimal(50000.00)
        SECOND_LEVEL = Decimal(100000.00)
        THIRD_LEVEL = Decimal(350000.00)
        FOURTH_LEVEL = Decimal(500000.00)

        ct_amount_first = self.get_queryset().filter(total_ct_cy__lte=FIRST_LEVEL)
        cash_transfers_amounts_first = [
            '$0-50,0000',
            ct_amount_first.filter(rating=PartnerOrganization.RATING_NON_ASSESSED).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_first.filter(rating=PartnerOrganization.RATING_LOW).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_first.filter(rating=PartnerOrganization.RATING_MODERATE).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_first.filter(rating=PartnerOrganization.RATING_SIGNIFICANT).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_first.filter(rating=PartnerOrganization.RATING_HIGH).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_first.aggregate(count=Count('total_ct_cy'))['count'],
        ]

        ct_amount_second = self.get_queryset().filter(total_ct_cy__gte=FIRST_LEVEL, total_ct_cy__lte=SECOND_LEVEL)
        cash_transfers_amounts_second = [
            '$50,0001-100,0000',
            ct_amount_second.filter(rating=PartnerOrganization.RATING_NON_ASSESSED).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_second.filter(rating=PartnerOrganization.RATING_LOW).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_second.filter(rating=PartnerOrganization.RATING_MODERATE).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_second.filter(rating=PartnerOrganization.RATING_SIGNIFICANT).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_second.filter(rating=PartnerOrganization.RATING_HIGH).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_second.aggregate(count=Count('total_ct_cy'))['count'],
        ]

        ct_amount_third = self.get_queryset().filter(total_ct_cy__gte=SECOND_LEVEL, total_ct_cy__lte=THIRD_LEVEL)
        cash_transfers_amounts_third = [
            '$100,0001-350,0000',
            ct_amount_third.filter(rating=PartnerOrganization.RATING_NON_ASSESSED).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_third.filter(rating=PartnerOrganization.RATING_LOW).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_third.filter(rating=PartnerOrganization.RATING_MODERATE).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_third.filter(rating=PartnerOrganization.RATING_SIGNIFICANT).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_third.filter(rating=PartnerOrganization.RATING_HIGH).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_third.aggregate(count=Count('total_ct_cy'))['count'],
        ]

        ct_amount_fourth = self.get_queryset().filter(total_ct_cy__gte=THIRD_LEVEL, total_ct_cy__lte=FOURTH_LEVEL)
        cash_transfers_amounts_fourth = [
            '$350,0001-500,0000',
            ct_amount_fourth.filter(rating=PartnerOrganization.RATING_NON_ASSESSED).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_fourth.filter(rating=PartnerOrganization.RATING_LOW).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_fourth.filter(rating=PartnerOrganization.RATING_MODERATE).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_fourth.filter(rating=PartnerOrganization.RATING_SIGNIFICANT).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_fourth.filter(rating=PartnerOrganization.RATING_HIGH).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_fourth.aggregate(count=Count('total_ct_cy'))['count'],
        ]

        ct_amount_fifth = self.get_queryset().filter(total_ct_cy__gte=FOURTH_LEVEL)
        cash_transfers_amounts_fifth = [
            '>$500,0000',
            ct_amount_fifth.filter(rating=PartnerOrganization.RATING_NON_ASSESSED).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_fifth.filter(rating=PartnerOrganization.RATING_LOW).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_fifth.filter(rating=PartnerOrganization.RATING_MODERATE).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_fifth.filter(rating=PartnerOrganization.RATING_SIGNIFICANT).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_fifth.filter(rating=PartnerOrganization.RATING_HIGH).aggregate(
                total=Coalesce(Sum('total_ct_cy'), 0))['total'],
            ct_amount_fifth.aggregate(count=Count('total_ct_cy'))['count'],
        ]

        return [
            ['Risk Rating', 'Not Required', 'Low', 'Medium', 'Significant', 'High', 'Number of IPs'],
            cash_transfers_amounts_first,
            cash_transfers_amounts_second,
            cash_transfers_amounts_third,
            cash_transfers_amounts_fourth,
            cash_transfers_amounts_fifth,
        ]

    def get_cash_transfer_risk_rating(self):

        total_ct_dict = {
            'total': Sum('total_ct_cy'),
            'count': Count('total_ct_cy')
        }

        high = self.get_queryset().filter(rating=PartnerOrganization.RATING_HIGH).aggregate(**total_ct_dict)
        significant = self.get_queryset().filter(
            rating=PartnerOrganization.RATING_SIGNIFICANT).aggregate(**total_ct_dict)
        moderate = self.get_queryset().filter(rating=PartnerOrganization.RATING_MODERATE).aggregate(**total_ct_dict)
        low = self.get_queryset().filter(rating=PartnerOrganization.RATING_LOW).aggregate(**total_ct_dict)
        non_assessed = self.get_queryset().filter(
            rating=PartnerOrganization.RATING_NON_ASSESSED).aggregate(**total_ct_dict)

        return [
            ['Risk Rating', 'Total Cash Transfers', {'role': 'style'}, 'Number of IPs'],
            ['Not Required', non_assessed['total'], '#D8D8D8', non_assessed['count']],
            ['Low', low['total'], '#2BB0F2', low['count']],
            ['Medium', moderate['total'], '#FECC02', moderate['count']],
            ['Significant', significant['total'], '#F05656', significant['count']],
            ['High', high['total'], '#751010', high['count']],
        ]

    def get_cash_transfer_partner_type(self):
        total_ct_dict = {
            'total': Sum('total_ct_cy'),
            'count': Count('total_ct_cy')
        }

        gov = self.get_queryset().filter(partner_type=PartnerType.GOVERNMENT).aggregate(**total_ct_dict)
        cso = self.get_queryset().filter(
            partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION).aggregate(**total_ct_dict)

        return [
            ['Partner Type', 'Total Cash Transfers', {'role': 'style'}, 'Number of Partners'],
            ['CSO', cso['total'], '#FECC02', cso['count']],
            ['GOV', gov['total'], '#F05656', gov['count']],
        ]

    def get_spot_checks_completed(self):
        qs = SpotCheck.objects.filter(status=Engagement.FINAL)
        return [
            ['Completed by', 'Count'],
            ['Staff', qs.filter(partner__vendor_number='0000000000').count()],
            ['Service Providers', qs.exclude(partner__vendor_number='0000000000').count()],
        ]

    def get_assurance_activities(self):

        today = date.today()
        deadline = today - timedelta(PartnerOrganization.EXPIRING_ASSESSMENT_LIMIT_DAYS)
        # TODO add filter for current year
        return {
            'programmatic_visits': {
                'completed': self._sum_json_values('hact_values__programmatic_visits__completed__total'),
                'min_required': sum([p.min_req_programme_visits for p in PartnerOrganization.objects.all()]),
            },
            'spot_checks': {
                'completed': self._sum_json_values('hact_values__spot_checks__completed__total'),
                'min_required': sum([p.min_req_spot_checks for p in PartnerOrganization.objects.all()]),
            },
            'scheduled_audit': Audit.objects.filter(status=Engagement.FINAL).count(),
            'special_audit': SpecialAudit.objects.filter(status=Engagement.FINAL).count(),
            'micro_assessment': MicroAssessment.objects.filter(status=Engagement.FINAL).count(),
            'missing_micro_assessment': PartnerOrganization.objects.filter(last_assessment_date__isnull=False,
                                                                           last_assessment_date__lte=deadline).count(),
        }

    def get_financial_findings(self):
        # TODO add filter for current year
        refunds = Audit.objects.filter(amount_refunded__isnull=False).aggregate(
            total=Coalesce(Sum('amount_refunded'), 0))['total']
        additional_supporting_document_provided = Audit.objects.filter(
            additional_supporting_documentation_provided__isnull=False, status=Engagement.FINAL).aggregate(
            total=Coalesce(Sum('additional_supporting_documentation_provided'), 0))['total']
        justification_provided_and_accepted = Audit.objects.filter(
            justification_provided_and_accepted__isnull=False).aggregate(
            total=Coalesce(Sum('justification_provided_and_accepted'), 0))['total']
        impairment = Audit.objects.filter(write_off_required__isnull=False).aggregate(
            total=Coalesce(Sum('write_off_required'), 0))['total']

        # pending_unsupported_amount property
        outstanding_audits = Audit.objects.filter(status=Engagement.FINAL)
        _ff = outstanding_audits.filter(financial_findings__isnull=False).aggregate(
            total=Coalesce(Sum('financial_findings'), 0))['total']
        _ar = outstanding_audits.filter(amount_refunded__isnull=False).aggregate(
            total=Coalesce(Sum('amount_refunded'), 0))['total']
        _asdp = outstanding_audits.filter(additional_supporting_documentation_provided__isnull=False).aggregate(
            total=Coalesce(Sum('additional_supporting_documentation_provided'), 0))['total']
        _wor = outstanding_audits.filter(write_off_required__isnull=False).aggregate(
            total=Coalesce(Sum('write_off_required'), 0))['total']
        outstanding = _ff - _ar - _asdp - _wor

        total_financial_findings = Audit.objects.filter(
            financial_findings__isnull=False, status=Engagement.FINAL).aggregate(
            total=Coalesce(Sum('financial_findings'), 0))['total']
        total_audited_expenditure = Audit.objects.filter(
            audited_expenditure__isnull=False, status=Engagement.FINAL).aggregate(
            total=Coalesce(Sum('audited_expenditure'), 0))['total']

        return [
            {
                'name': 'Total Audited Expenditure',
                'value': total_audited_expenditure,
                'highlighted': False,
            },
            {
                'name': 'Total Financial Findings',
                'value': total_financial_findings,
                'highlighted': True,
            },
            {
                'name': 'Refunds',
                'value': refunds,
                'highlighted': False,
            },
            {
                'name': 'Additional Supporting Documentation Received',
                'value': additional_supporting_document_provided,
                'highlighted': False,
            },
            {
                'name': 'Justification Provided and Accepted',
                'value': justification_provided_and_accepted,
                'highlighted': False,
            },
            {
                'name': 'Impairment',
                'value': impairment,
                'highlighted': False,
            },
            {
                'name': 'Outstanding(Requires Follow-up)',
                'value': outstanding,
                'highlighted': True,
            }
        ]

    def get_financial_findings_numbers(self):
        return [
            {
                'name': 'Number of High Priority Findings',
                'value': Audit.objects.filter(risks__value=4).count(),  # TODO add filter for current year
            },
            {
                'name': 'Number of Medium Priority Findings',
                'value': Audit.objects.filter(risks__value=2).count(),  # TODO add filter for current year
            },
            {
                'name': 'Number of Low Priority Findings',
                'value': Audit.objects.filter(risks__value=1).count(),  # TODO add filter for current year
            },
            {
                'name': 'Audit Opinion',
                'value': Audit.objects.filter(risks__value=0).count(),  # TODO add filter for current year
                # 'value': [
                #     {
                #         'name': 'qualified',
                #         'value': 34,
                #     },
                #     {
                #         'name': 'unqualified',
                #         'value': 22,
                #     },
                #     {
                #         'name': 'denial',
                #         'value': 10
                #     },
                #     {
                #         'name': 'adverse',
                #         'value': 40
                #     },
                # ],
            }
        ]

    def get(self, request, *args, **kwargs):
        return Response(
            {
                'assurance_activities': self.get_assurance_activities(),
                'financial_findings': self.get_financial_findings(),
                'financial_findings_numbers': self.get_financial_findings_numbers(),
                'charts': {
                    'cash_transfers_amounts': self.cash_transfers_amounts(),
                    'cash_transfers_risk_ratings': self.get_cash_transfer_risk_rating(),
                    'cash_transfers_partner_type': self.get_cash_transfer_partner_type(),
                    'spot_checks_completed': self.get_spot_checks_completed(),
                },
            }
        )
