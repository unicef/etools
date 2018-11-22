from datetime import date

from django.db import models

from rest_framework.filters import BaseFilterBackend

from etools.applications.field_monitoring.settings.models import LogIssue


class CPOutputIsActiveFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        filter_value = request.query_params.get('is_active')
        if filter_value is None:
            return queryset

        if filter_value.lower() == 'true':
            return queryset.filter(to_date__gte=date.today())
        else:
            return queryset.filter(to_date__lt=date.today())


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
            elif value == LogIssue.RELATED_TO_TYPE_CHOICES.location_site:
                filters |= models.Q(models.Q(location__isnull=False) | models.Q(location_site__isnull=False))

        return queryset.filter(filters)


class LogIssueVisitFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        filter_value = request.query_params.get('visit')
        if filter_value is None:
            return queryset

        raise NotImplementedError
