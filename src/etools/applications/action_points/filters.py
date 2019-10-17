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
        if not related_module:
            return queryset

        related_instance_filters = {
            ActionPoint.MODULE_CHOICES.t2f: {'travel_activity__isnull': False},
            ActionPoint.MODULE_CHOICES.tpm: {'tpm_activity__isnull': False},
            ActionPoint.MODULE_CHOICES.psea: {'psea_assessment__isnull': False},
            ActionPoint.MODULE_CHOICES.audit: {'engagement__isnull': False},
            ActionPoint.MODULE_CHOICES.apd: {
                'travel_activity__isnull': True,
                'tpm_activity__isnull': True,
                'psea_assessment__isnull': True,
                'engagement__isnull': True
            },
        }
        if related_module not in related_instance_filters:
            return queryset

        return queryset.filter(**related_instance_filters[related_module])
