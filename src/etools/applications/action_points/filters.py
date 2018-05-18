from django.db.models.functions import TruncYear

from rest_framework.filters import BaseFilterBackend

from etools.applications.action_points.models import ActionPoint


class ReferenceNumberOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get('ordering', '')
        if not ordering.lstrip('-') == 'reference_number':
            return queryset

        asc_desc = "-" if ordering.startswith("-") else ""
        ordering_params = ["{}{}".format(asc_desc, param) for param in ["created_year", "id"]]
        return queryset.annotate(created_year=TruncYear("created")).order_by(*ordering_params)


class RelatedModuleFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        related_module = request.query_params.get('related_module', '')
        if related_module:
            return queryset

        related_instance_fields = {
            ActionPoint.MODULE_CHOICES.t2f: 'travel_activity',
            ActionPoint.MODULE_CHOICES.tpm: 'tpm_activity',
            ActionPoint.MODULE_CHOICES.audit: 'engagement',
        }
        if related_module not in related_instance_fields:
            return queryset

        return queryset.filter(**{'{}__isnull'.format(related_instance_fields[related_module]): False})
