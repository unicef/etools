from django.db.models import Count, Max, Min, OuterRef, Prefetch, Q

from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from etools.applications.action_points.models import ActionPoint
from etools.applications.field_monitoring.analyze.serializers import (
    CoverageGeographicSerializer,
    CPOutputCoverageSerializer,
    CPOutputIssuesSerializer,
    HACTSerializer,
    InterventionCoverageSerializer,
    LocationIssuesSerializer,
    OverallSerializer,
    PartnerIssuesSerializer,
    PartnersCoverageSerializer,
)
from etools.applications.field_monitoring.fm_settings.models import LogIssue
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.utils.models import SubQueryCount
from etools.applications.locations.models import Location
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.reports.models import Result, ResultType


class OverallView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(data=OverallSerializer(instance=object).data)  # todo: this looks very strange. should be fixed


_completed_activities_filter = Q(monitoring_activities__status=MonitoringActivity.STATUSES.completed)


class HACTView(ListAPIView):
    serializer_class = HACTSerializer

    queryset = PartnerOrganization.objects.filter(
        monitoring_activities__isnull=False
    ).prefetch_related(
        Prefetch(
            'monitoring_activities',
            MonitoringActivity.objects.filter(
                status=MonitoringActivity.STATUSES.completed

            ).prefetch_related('cp_outputs', 'interventions'),
            to_attr='visits'
        ),
    ).order_by('id').distinct()


class CoveragePartnersView(ListAPIView):
    serializer_class = PartnersCoverageSerializer
    queryset = PartnerOrganization.objects.filter(
        monitoring_activities__isnull=False
    ).annotate(
        completed_visits=Count('monitoring_activities', filter=_completed_activities_filter),
        last_visit=Max('monitoring_activities__end_date', filter=_completed_activities_filter),
    ).order_by('id').distinct()


class CoverageInterventionsView(ListAPIView):
    serializer_class = InterventionCoverageSerializer
    queryset = Intervention.objects.filter(
        monitoring_activities__isnull=False
    ).annotate(
        completed_visits=Count('monitoring_activities', filter=_completed_activities_filter),
        first_visit=Min('monitoring_activities__end_date', filter=_completed_activities_filter),
        last_visit=Max('monitoring_activities__end_date', filter=_completed_activities_filter),
    ).order_by('id').distinct().prefetch_related(None)  # no need to use any prefetch here


class CoverageCPOutputsView(ListAPIView):
    serializer_class = CPOutputCoverageSerializer
    queryset = Result.objects.filter(
        result_type__name=ResultType.OUTPUT, monitoring_activities__isnull=False
    ).annotate(
        completed_visits=Count('monitoring_activities', filter=_completed_activities_filter),
        first_visit=Min('monitoring_activities__end_date', filter=_completed_activities_filter),
        last_visit=Max('monitoring_activities__end_date', filter=_completed_activities_filter),
    ).order_by('id').distinct()


class CoverageGeographicView(ListAPIView):
    serializer_class = CoverageGeographicSerializer
    queryset = Location.objects.filter(parent__admin_level=0)

    def get_queryset(self):
        queryset = super().get_queryset()

        activities_filter = Q(
            status=MonitoringActivity.STATUSES.completed,
            location__lft__gte=OuterRef('lft'),
            location__lft__lte=OuterRef('rght'),
            location__tree_id=OuterRef('tree_id'),
        )

        if 'sections__in' in self.request.query_params:
            activities_filter = activities_filter & Q(
                sections__in=self.request.query_params['sections__in'].split(',')
            )

        queryset = queryset.annotate(
            completed_visits=SubQueryCount(MonitoringActivity.objects.filter(activities_filter).distinct('id')),
        )

        return queryset


class IssuesPartnersView(ListAPIView):
    serializer_class = PartnerIssuesSerializer
    queryset = PartnerOrganization.objects.filter(
        Q(log_issues__isnull=False) | Q(actionpoint__isnull=False)
    ).annotate(
        log_issues_count=SubQueryCount(
            LogIssue.objects.filter(status=LogIssue.STATUS_CHOICES.new, partner_id=OuterRef('id'))
        ),
        action_points_count=SubQueryCount(
            ActionPoint.objects.filter(status=ActionPoint.STATUS_OPEN, partner_id=OuterRef('id'))
        ),
    ).order_by('id').distinct()


class IssuesCPOutputsView(ListAPIView):
    serializer_class = CPOutputIssuesSerializer
    queryset = Result.objects.filter(
        Q(log_issues__isnull=False) | Q(actionpoint__isnull=False),
        result_type__name=ResultType.OUTPUT
    ).annotate(
        log_issues_count=SubQueryCount(
            LogIssue.objects.filter(status=LogIssue.STATUS_CHOICES.new, cp_output_id=OuterRef('id'))
        ),
        action_points_count=SubQueryCount(
            ActionPoint.objects.filter(status=ActionPoint.STATUS_OPEN, cp_output_id=OuterRef('id'))
        ),
    ).order_by('id').distinct()


class IssuesLocationsView(ListAPIView):
    serializer_class = LocationIssuesSerializer
    queryset = Location.objects.filter(
        Q(log_issues__isnull=False) | Q(actionpoint__isnull=False)
    ).annotate(
        log_issues_count=SubQueryCount(
            LogIssue.objects.filter(status=LogIssue.STATUS_CHOICES.new, location_id=OuterRef('id'))
        ),
        action_points_count=SubQueryCount(
            ActionPoint.objects.filter(status=ActionPoint.STATUS_OPEN, location_id=OuterRef('id'))
        ),
    ).order_by('id').distinct()
