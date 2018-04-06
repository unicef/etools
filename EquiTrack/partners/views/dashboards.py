from __future__ import unicode_literals

from datetime import datetime
from django.db.models import F, Max, DurationField, ExpressionWrapper, Min, Sum, Count, CharField

from rest_framework.generics import (
    ListCreateAPIView
)
from rest_framework.permissions import IsAdminUser
from rest_framework_csv import renderers as r

from partners.models import (
    Intervention,
)
from partners.exports_v2 import PartnershipDashCSVRenderer
from partners.serializers.dashboards import InterventionDashSerializer


class InterventionPartnershipDashView(ListCreateAPIView):
    """InterventionDashView
    Returns a list of Interventions.
    """
    serializer_class = InterventionDashSerializer
    permission_classes = (IsAdminUser,)
    renderer_classes = (r.JSONRenderer, PartnershipDashCSVRenderer)

    def get_queryset(self):
        today = datetime.now()
        delta = ExpressionWrapper(today - F('last_pv_date'), output_field=DurationField())

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
            # last_pv_date=Max(
            #     Case(
            #         When(
            #             travel_activities__travel_type=TravelType.PROGRAMME_MONITORING,
            #             travel_activities__travels__traveler=F(
            #                 'travel_activities__primary_traveler'
            #             ),
            #             travel_activities__travels__status=Travel.COMPLETED,
            #             then=F('travel_activities__date')
            #         ),
            #         output_field=DateTimeField()
            #     )
            # ),
        )
        qs = qs.annotate(days_since_last_pv=delta)
        return qs.order_by('agreement__partner__name')

    def list(self, request):
        """
            Checks for format query parameter
            :returns: JSON or CSV file
        """
        query_params = self.request.query_params
        response = super().list(request)
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                response['Content-Disposition'] = "attachment;filename=partnership-dash.csv"

        return response
