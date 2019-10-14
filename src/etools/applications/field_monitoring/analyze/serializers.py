from django.utils import timezone
from rest_framework import serializers
from rest_framework.fields import ReadOnlyField
from unicef_locations.models import Location

from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.partners.models import PartnerOrganization, Intervention
from etools.applications.partners.serializers.interventions_v2 import MinimalInterventionListSerializer
from etools.applications.reports.models import Result
from etools.applications.reports.serializers.v2 import MinimalOutputListSerializer


class OverallSerializer(serializers.Serializer):
    visits_completed = serializers.SerializerMethodField()
    visits_planned = serializers.SerializerMethodField()

    def get_visits_completed(self, obj):
        return MonitoringActivity.objects.filter(status=MonitoringActivity.STATUSES.completed).count()

    def get_visits_planned(self, obj):
        return 0


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
        return 0

    def get_days_since_visit(self, obj):
        if not obj.last_visit:
            return None

        return (timezone.now().date() - obj.last_visit).days


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
        if not obj.last_visit:
            return None

        return (timezone.now().date() - obj.last_visit).days

    def get_avg_days_between_visits(self, obj):
        if obj.completed_visits in [0, 1]:  # nothing to calculate
            return None

        if not obj.last_visit or not obj.first_visit:  # possible only for corrupted data; dates are required
            return None

        return int((obj.last_visit - obj.first_visit).days / (obj.completed_visits - 1))


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
        if not obj.last_visit:
            return None

        return (timezone.now().date() - obj.last_visit).days

    def get_avg_days_between_visits(self, obj):
        if obj.completed_visits in [0, 1]:  # nothing to calculate
            return None

        if not obj.last_visit or not obj.first_visit:  # possible only for corrupted data; dates are required
            return None

        return int((obj.last_visit - obj.first_visit).days / (obj.completed_visits - 1))


class CoverageGeographicSerializer(serializers.ModelSerializer):
    completed_visits = serializers.ReadOnlyField()

    class Meta:
        model = Location
        fields = [
            'id', 'name',
            'completed_visits', 'geom'
        ]


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
    visits_count = ReadOnlyField(source='completed_visits')

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
