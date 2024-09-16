import functools
import operator

from django.contrib.contenttypes.models import ContentType
from django.db.models import Case, CharField, Count, F, Max, Min, OuterRef, Q, Subquery, Sum, When

from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework_csv import renderers as r
from unicef_attachments.models import Attachment
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.action_points.models import ActionPoint
from etools.applications.partners.exports_v2 import PartnershipDashCSVRenderer
from etools.applications.partners.models import Intervention
from etools.applications.partners.serializers.dashboards import InterventionDashSerializer
from etools.applications.t2f.models import Travel, TravelActivity, TravelType
from etools.libraries.djangolib.models import MaxDistinct


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
    )
    search_terms = ('agreement__partner__name__icontains', )

    def get_queryset(self):
        final_partnership_review_qs = Attachment.objects.filter(
            content_type_id=ContentType.objects.get_for_model(Intervention).id,
            object_id=OuterRef("pk"),
            file_type__name='final_partnership_review',
        ).values("pk")[:1]

        action_points_qs = Intervention.objects.filter(
            pk=OuterRef("pk")
        ).annotate(
            total=Count(
                "actionpoint",
                filter=Q(actionpoint__status=ActionPoint.STATUS_OPEN),
            )
        ).values("total")

        last_pv_date_qs = TravelActivity.objects.filter(
            partnership__pk=OuterRef("pk"),
            travel_type=TravelType.PROGRAMME_MONITORING,
            travels__traveler=F('primary_traveler'),
            travels__status=Travel.COMPLETED,
        ).values("date").order_by("-date")[:1]

        qs = Intervention.objects.exclude(
            status__in=[Intervention.DRAFT],
        ).prefetch_related(
            'agreement__partner',
        )
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
            max_fr_currency=MaxDistinct("frs__currency", output_field=CharField(), distinct=True),
            multi_curr_flag=Count(Case(When(frs__multi_curr_flag=True, then=1))),
            has_final_partnership_review=Subquery(final_partnership_review_qs),
            action_points=Subquery(action_points_qs),
            last_pv_date=Subquery(last_pv_date_qs),
        )

        query_params = self.request.query_params
        if query_params:
            queries = []
            queries.extend(self.filter_params())
            queries.append(self.search_params())

            if queries:
                expression = functools.reduce(operator.and_, queries)
                qs = qs.filter(expression)

        return qs.order_by('agreement__partner__organization__name')

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
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)

        response = Response(serializer.data)
        if "format" in query_params.keys():
            if query_params.get("format") == 'csv':
                response['Content-Disposition'] = "attachment;filename=partnership-dash.csv"

        return response
