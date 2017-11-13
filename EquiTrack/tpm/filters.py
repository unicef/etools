from __future__ import absolute_import, division, print_function, unicode_literals

from django.db.models.lookups import YearTransform

from rest_framework.filters import BaseFilterBackend


class ReferenceNumberOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get('ordering', '')
        if not ordering.lstrip('-') == 'reference_number':
            return queryset

        ordering_params = ['created_year', 'id']

        return queryset.annotate(created_year=YearTransform('created'))\
            .order_by(*map(lambda param: ('' if ordering == 'reference_number' else '-') + param, ordering_params))
