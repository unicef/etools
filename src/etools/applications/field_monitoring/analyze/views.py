from django.db.models import Prefetch, Count, Q, Max, Min
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from unicef_locations.models import Location

from etools.applications.field_monitoring.analyze.serializers import OverallSerializer, HACTSerializer, \
    PartnersCoverageSerializer, InterventionCoverageSerializer, CPOutputCoverageSerializer, CoverageGeographicSerializer
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.partners.models import PartnerOrganization, Intervention
from etools.applications.reports.models import Result, ResultType


class OverallView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(data=OverallSerializer(instance=object).data)  # todo: this looks very strange. should be fixed


class HACTView(ListAPIView):
    serializer_class = HACTSerializer
    queryset = PartnerOrganization.objects.filter(monitoring_activities__isnull=False).order_by('id').distinct()
    queryset = queryset.annotate(
        visits_count=Count(
            'monitoring_activities',
            filter=Q(monitoring_activities__status=MonitoringActivity.STATUSES.completed)
        ),
    )
    queryset = queryset.prefetch_related(
        Prefetch(
            'monitoring_activities',
            MonitoringActivity.objects.filter(
                status=MonitoringActivity.STATUSES.completed
            ).prefetch_related('cp_outputs', 'interventions'),
            to_attr='visits'
        )
    )


class CoveragePartnersView(ListAPIView):
    serializer_class = PartnersCoverageSerializer
    queryset = PartnerOrganization.objects.filter(monitoring_activities__isnull=False).order_by('id').distinct()
    queryset = queryset.annotate(
        completed_visits=Count(
            'monitoring_activities',
            filter=Q(monitoring_activities__status=MonitoringActivity.STATUSES.completed)
        ),
        last_visit=Max(
            'monitoring_activities__end_date',
            filter=Q(monitoring_activities__status=MonitoringActivity.STATUSES.completed)
        )
    )


class CoverageInterventionsView(ListAPIView):
    serializer_class = InterventionCoverageSerializer
    queryset = Intervention.objects.filter(monitoring_activities__isnull=False).order_by('id').distinct()
    queryset = queryset.annotate(
        completed_visits=Count(
            'monitoring_activities',
            filter=Q(monitoring_activities__status=MonitoringActivity.STATUSES.completed)
        ),
        first_visit=Min(
            'monitoring_activities__end_date',
            filter=Q(monitoring_activities__status=MonitoringActivity.STATUSES.completed)
        ),
        last_visit=Max(
            'monitoring_activities__end_date',
            filter=Q(monitoring_activities__status=MonitoringActivity.STATUSES.completed)
        )
    )
    queryset = queryset.prefetch_related(None)  # no need to use any prefetch here


class CoverageCPOutputsView(ListAPIView):
    serializer_class = CPOutputCoverageSerializer
    queryset = Result.objects.filter(
        result_type__name=ResultType.OUTPUT, monitoring_activities__isnull=False
    ).order_by('id').distinct()
    queryset = queryset.annotate(
        completed_visits=Count(
            'monitoring_activities',
            filter=Q(monitoring_activities__status=MonitoringActivity.STATUSES.completed)
        ),
        first_visit=Min(
            'monitoring_activities__end_date',
            filter=Q(monitoring_activities__status=MonitoringActivity.STATUSES.completed)
        ),
        last_visit=Max(
            'monitoring_activities__end_date',
            filter=Q(monitoring_activities__status=MonitoringActivity.STATUSES.completed)
        )
    )


class CoverageGeographicView(ListAPIView):
    serializer_class = CoverageGeographicSerializer
    queryset = Location.objects.filter(parent__gateway__admin_level=0)
    queryset = queryset.annotate(
        completed_visits=Count(
            'monitoring_activities',
            filter=Q(monitoring_activities__status=MonitoringActivity.STATUSES.completed)
        ),
    )
