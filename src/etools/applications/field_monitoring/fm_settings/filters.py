from datetime import date

from django.db import models
from django.db.models import Case, When, F

from rest_framework.filters import BaseFilterBackend

from etools.applications.field_monitoring.fm_settings.models import LogIssue


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
            elif value == LogIssue.RELATED_TO_TYPE_CHOICES.location:
                filters |= models.Q(models.Q(location__isnull=False) | models.Q(location_site__isnull=False))

        return queryset.filter(filters)


class LogIssueVisitFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        filter_value = request.query_params.get('visit')
        if filter_value is None:
            return queryset

        return queryset.filter(
            models.Q(cp_output__fm_config__tasks__visits=filter_value) |
            models.Q(partner__tasks__visits=filter_value) |
            models.Q(location__tasks__visits=filter_value) |
            models.Q(location__visits=filter_value) |
            models.Q(location_site__tasks__visits=filter_value) |
            models.Q(location_site__visits=filter_value)
        ).distinct()


class LogIssueNameOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get('ordering', '')
        if not ordering.lstrip('-') == 'name':
            return queryset

        return queryset.annotate(name=Case(
            When(cp_output__isnull=False, then=F('cp_output__name')),
            When(partner__isnull=False, then=F('partner__name')),
            When(location_site__isnull=False, then=F('location_site__name')),
            When(location__isnull=False, then=F('location__name')),
            output_field=models.CharField()
        )).order_by(ordering)
