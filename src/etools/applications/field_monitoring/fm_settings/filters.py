from django.db import models
from django.db.models import Case, F, When

from django_filters import rest_framework as filters
from rest_framework.filters import BaseFilterBackend

from etools.applications.field_monitoring.fm_settings.models import LogIssue, Question
from etools.applications.field_monitoring.utils.filters import M2MInFilter


class LogIssueRelatedToTypeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        filter_value = request.query_params.get('related_to_type')
        if filter_value is None:
            return queryset

        filters = models.Q()
        for value in filter_value.split(','):
            if value == LogIssue.RELATED_TO_TYPE_CHOICES.cp_output:
                filters |= models.Q(cp_output__isnull=False)
            elif value == LogIssue.RELATED_TO_TYPE_CHOICES.partner:
                filters |= models.Q(partner__isnull=False)
            elif value == LogIssue.RELATED_TO_TYPE_CHOICES.location:
                filters |= models.Q(models.Q(location__isnull=False) | models.Q(location_site__isnull=False))

        return queryset.filter(filters)


class LogIssueMonitoringActivityFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        activity = request.query_params.get('activity')
        if activity is None:
            return queryset

        return queryset.filter(
            models.Q(cp_output__monitoring_activities=activity) |
            models.Q(partner__monitoring_activities=activity) |
            models.Q(location__monitoring_activities=activity) |
            models.Q(location_site__monitoring_activities=activity)
        ).distinct()


class LogIssueNameOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get('ordering', '')
        if not ordering.lstrip('-') == 'name':
            return queryset

        return queryset.annotate(name=Case(
            When(cp_output__isnull=False, then=F('cp_output__name')),
            When(partner__isnull=False, then=F('partner__organization__name')),
            When(location_site__isnull=False, then=F('location_site__name')),
            When(location__isnull=False, then=F('location__name')),
            output_field=models.CharField()
        )).order_by(ordering)


class QuestionsFilterSet(filters.FilterSet):
    methods__in = M2MInFilter(field_name="methods")
    sections__in = M2MInFilter(field_name="sections")

    class Meta:
        model = Question
        fields = {
            'level': ['exact', 'in'],
            'category': ['exact', 'in'],
            'answer_type': ['exact', 'in'],
            'is_hact': ['exact'],
            'is_active': ['exact'],
            'is_custom': ['exact'],
            'methods': ['in'],
            'sections': ['in'],
        }
