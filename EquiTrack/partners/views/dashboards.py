from __future__ import unicode_literals

from datetime import datetime
from django.db.models import Case, When, F, Max, DateTimeField, DurationField, ExpressionWrapper, Min, Sum, Count, \
    CharField

from rest_framework_csv import renderers as r
from rest_framework.permissions import IsAdminUser
from rest_framework.generics import (
    ListCreateAPIView
)
from rest_framework.response import Response

from partners.models import (
    Intervention,
)
from partners.exports_v2 import PartnershipDashCSVRenderer
from partners.serializers.dashboards import InterventionDashSerializer
from t2f.models import Travel, TravelType


class InterventionPartnershipDashView(ListCreateAPIView):
    """InterventionDashView
    Returns a list of Interventions.
    """
    serializer_class = InterventionDashSerializer
    permission_classes = (IsAdminUser,)
    renderer_classes = (r.JSONRenderer, PartnershipDashCSVRenderer)

    def get_queryset(self):
        qs = Intervention.objects.exclude(status=Intervention.DRAFT).annotate(
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
            max_fr_currency=Max("frs__currency", output_field=CharField(), distinct=True),
            multi_curr_flag=Count(Case(When(frs__multi_curr_flag=True, then=1)))
        )

        return qs.order_by('agreement__partner__name')

    def append_last_pv_date(self, serializer):
        delta = ExpressionWrapper(
            datetime.now() - F('last_pv_date'),
            output_field=DurationField()
        )
        qs = Intervention.objects.exclude(
            status=Intervention.DRAFT
        ).annotate(
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
            )
        )
        qs = qs.annotate(days_since_last_pv=delta)
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

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            self.append_last_pv_date(serializer)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        self.append_last_pv_date(serializer)

        response = Response(serializer.data)
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                response['Content-Disposition'] = "attachment;filename=partnership-dash.csv"

        return response
