import json

from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.db.models import Max

from rest_framework import serializers

from etools.applications.field_monitoring.analyze.utils import get_avg_days_between_visits, get_days_since_last_visit
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.locations.models import Location
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.partners.serializers.interventions_v2 import MinimalInterventionListSerializer
from etools.applications.reports.models import Result
from etools.applications.reports.serializers.v2 import MinimalOutputListSerializer


class OverallSerializer(serializers.Serializer):
    visits_completed = serializers.SerializerMethodField()
    visits_planned = serializers.SerializerMethodField()

    def get_visits_completed(self, obj):
        return MonitoringActivity.objects.filter(status=MonitoringActivity.STATUSES.completed).count()

    def get_visits_planned(self, obj):
        def _rec_key_text(keys):
            head = keys.pop()
            if not keys:
                return head
            return KeyTextTransform(head, _rec_key_text(keys))
        exp = _rec_key_text(['hact_values', 'programmatic_visits', 'planned', 'total'])
        return PartnerOrganization.objects.annotate(visits=exp).aggregate(max=Max('visits'))['max'] or 0


class PartnersCoverageSerializer(serializers.ModelSerializer):
    completed_visits = serializers.ReadOnlyField()
    planned_visits = serializers.SerializerMethodField()
    minimum_required_visits = serializers.ReadOnlyField(source='min_req_programme_visits')
    days_since_visit = serializers.SerializerMethodField()

    class Meta:
        model = PartnerOrganization
        fields = [
            'id', 'name',
            'completed_visits', 'planned_visits', 'minimum_required_visits',
            'days_since_visit',
        ]

    def get_planned_visits(self, obj):
        return obj.hact_values["programmatic_visits"]["planned"]["total"] or 0

    def get_days_since_visit(self, obj):
        return get_days_since_last_visit(obj)


class InterventionCoverageSerializer(serializers.ModelSerializer):
    days_since_visit = serializers.SerializerMethodField()
    avg_days_between_visits = serializers.SerializerMethodField()

    class Meta:
        model = Intervention
        fields = [
            'id', 'number',
            'days_since_visit', 'avg_days_between_visits',
        ]

    def get_days_since_visit(self, obj):
        return get_days_since_last_visit(obj)

    def get_avg_days_between_visits(self, obj):
        return get_avg_days_between_visits(obj)


class CPOutputCoverageSerializer(serializers.ModelSerializer):
    days_since_visit = serializers.SerializerMethodField()
    avg_days_between_visits = serializers.SerializerMethodField()

    class Meta:
        model = Result
        fields = [
            'id', 'name',
            'days_since_visit', 'avg_days_between_visits',
        ]

    def get_days_since_visit(self, obj):
        return get_days_since_last_visit(obj)

    def get_avg_days_between_visits(self, obj):
        return get_avg_days_between_visits(obj)


class CoverageGeographicSerializer(serializers.ModelSerializer):
    completed_visits = serializers.ReadOnlyField()
    geom = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = [
            'id', 'name',
            'completed_visits', 'geom'
        ]

    def get_geom(self, obj):
        if not obj.geom:
            return {}

        # simplify geometry to avoid huge polygons
        return json.loads(obj.geom.simplify(0.003).json)


class MonitoringActivityHACTSerializer(serializers.ModelSerializer):
    cp_outputs = MinimalOutputListSerializer(many=True)
    interventions = MinimalInterventionListSerializer(many=True)

    class Meta:
        model = MonitoringActivity
        fields = [
            'id', 'reference_number',
            'cp_outputs', 'interventions',
            'end_date',
        ]


class HACTSerializer(serializers.ModelSerializer):
    visits = MonitoringActivityHACTSerializer(many=True)
    visits_count = serializers.SerializerMethodField()

    def get_visits_count(self, obj):
        try:
            return obj.hact_values["programmatic_visits"]["completed"]["total"]
        except KeyError:
            return 0

    class Meta:
        model = PartnerOrganization
        fields = [
            'id', 'name',
            'visits', 'visits_count',
        ]


class PartnerIssuesSerializer(serializers.ModelSerializer):
    log_issues_count = serializers.ReadOnlyField()
    action_points_count = serializers.ReadOnlyField()

    class Meta:
        model = PartnerOrganization
        fields = [
            'id', 'name',
            'log_issues_count', 'action_points_count'
        ]


class CPOutputIssuesSerializer(serializers.ModelSerializer):
    log_issues_count = serializers.ReadOnlyField()
    action_points_count = serializers.ReadOnlyField()

    class Meta:
        model = Result
        fields = [
            'id', 'name',
            'log_issues_count', 'action_points_count'
        ]


class LocationIssuesSerializer(serializers.ModelSerializer):
    log_issues_count = serializers.ReadOnlyField()
    action_points_count = serializers.ReadOnlyField()

    class Meta:
        model = Result
        fields = [
            'id', 'name',
            'log_issues_count', 'action_points_count'
        ]
