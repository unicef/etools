import functools
import operator
from datetime import datetime, timedelta

from django.db.models import (
    Case,
    CharField,
    Count,
    DateTimeField,
    DurationField,
    ExpressionWrapper,
    F,
    Max,
    Min,
    Sum,
    When,
)

from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework_csv import renderers as r
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.partners.exports_v2 import PartnershipDashCSVRenderer
from etools.applications.partners.models import FileType, Intervention
from etools.applications.partners.serializers.dashboards import InterventionDashSerializer
from etools.applications.t2f.models import Travel, TravelType


class InterventionPartnershipDashView(QueryStringFilterMixin, ListCreateAPIView):
    """InterventionDashView Returns a list of Interventions."""
    serializer_class = InterventionDashSerializer
    permission_classes = (IsAdminUser,)
    renderer_classes = (r.JSONRenderer, PartnershipDashCSVRenderer)

    search_param = 'qs'
    filters = (
        ('pk', 'pk__in'),
        ('status', 'status__in'),
        ('startAfter', 'start__gt'),
        ('startBefore', 'start__lt'),
        ('endAfter', 'end__gt'),
        ('endBefore', 'end__lt'),
        ('offices', 'offices__name__in'),
        ('sectors', 'sections__in'),
        ('alerts', {
            'expired_without_FR': [('status', 'signed'),
                                   ('start__lt', datetime.today()),
                                   ('frs__total_amt_local__sum__gt', 0)],
            'planned_amount_different_FR': [('status__in', ['active', 'ended', 'suspended']),
                                            ('planned_difference__gt', 0)],
            'no_recent_PV': [('status__in', ['active', 'ended']),
                             ('days_since_last_pv__gt', timedelta(180))],
            'expiring': [('status__in', ['active', 'ended'],
                          ('end__gt', datetime.today()),
                          ('end__lt', datetime.today() - timedelta(days=30)))],
            'disbursment_less_FR_planned': [('status', 'ended'),
                                            ('disbursment_planned_difference__gt', 0)],
            'missing_final_partnership_review': [('status', 'ended'),
                                                 ('has_final_partnership_review', 0),
                                                 ('frs__actual_amt__sum__gt', 100000)],
        })
    )
    search_terms = ('agreement__partner__name__icontains', )

    def get_queryset(self):
        qs = Intervention.objects.exclude(status=Intervention.DRAFT).prefetch_related('agreement__partner')
        qs = qs.annotate(
            Max("frs__end_date"),
            Min("frs__start_date"),
            Sum("frs__total_amt"),
            Sum("frs__total_amt_local"),
            Sum("frs__intervention_amt"),
            Sum("frs__outstanding_amt_local"),
            Sum("frs__outstanding_amt"),
            Sum("frs__actual_amt"),
            Sum("frs__actual_amt_local"),
            Count("frs__currency", distinct=True),
            planned_difference=Sum("frs__total_amt_local") - F('planned_budget__unicef_cash_local'),
            disbursment_planned_difference=Sum("frs__total_amt_local") - Sum("frs__actual_amt_local"),

            max_fr_currency=Max("frs__currency", output_field=CharField(), distinct=True),
            multi_curr_flag=Count(Case(When(frs__multi_curr_flag=True, then=1))),
            has_final_partnership_review=Count(Case(When(attachments__type__name=FileType.FINAL_PARTNERSHIP_REVIEW,
                                                         then=1))),
            last_pv_date=Max(
                Case(
                    When(
                        travel_activities__travel_type=TravelType.PROGRAMME_MONITORING,
                        travel_activities__travels__traveler=F(
                            'travel_activities__primary_traveler'
                        ),
                        travel_activities__travels__status=Travel.COMPLETED,
                        then=F('travel_activities__date')
                    ),
                    output_field=DateTimeField()
                )
            ),
            days_since_last_pv=ExpressionWrapper(datetime.now() - F('last_pv_date'), output_field=DurationField()),
        )

        query_params = self.request.query_params
        if query_params:
            queries = []
            queries.extend(self.filter_params())
            queries.append(self.search_params())

            if queries:
                expression = functools.reduce(operator.and_, queries)
                qs = qs.filter(expression)

        return qs.order_by('agreement__partner__name')

    def append_final_partnership_review(self, serializer):
        qs = self.get_queryset()
        fpr = {}
        for i in qs:
            fpr[str(i.pk)] = {
                "has_final_partnership_review": i.has_final_partnership_review,
            }
        # Add last_pv_date
        for d in serializer.data:
            pk = d["intervention_id"]
            d["has_final_partnership_review"] = bool(fpr[pk]["has_final_partnership_review"])
        return serializer

    def append_last_pv_date(self, serializer):
        qs = self.get_queryset()
        pv_dates = {}
        for i in qs:
            pv_dates[str(i.pk)] = {
                "last_pv_date": i.last_pv_date,
                "days_last_pv": i.days_since_last_pv.days if i.days_since_last_pv else None,
            }
        # Add last_pv_date
        for d in serializer.data:
            pk = d["intervention_id"]
            d["last_pv_date"] = pv_dates[pk]["last_pv_date"]
            d["days_last_pv"] = pv_dates[pk]["days_last_pv"]
        return serializer

    def list(self, request):
        """
            Checks for format query parameter
            :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        queryset = self.filter_queryset(self.get_queryset())

        if self.paginator:
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page, many=True)
            self.append_last_pv_date(serializer)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        self.append_last_pv_date(serializer)
        self.append_final_partnership_review(serializer)

        response = Response(serializer.data)
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                response['Content-Disposition'] = "attachment;filename=partnership-dash.csv"

        return response
