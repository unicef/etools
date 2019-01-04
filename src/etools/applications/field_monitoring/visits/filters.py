from django.db.models import Count
from django.db.models.functions import TruncYear
from rest_framework.filters import BaseFilterBackend


class ReferenceNumberOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get('ordering', '')
        if not ordering.lstrip('-') == 'reference_number':
            return queryset

        ordering_params = ['created_year', 'id']

        return queryset.annotate(created_year=TruncYear('created'))\
            .order_by(*map(lambda param: ('' if ordering == 'reference_number' else '-') + param, ordering_params))

#
# class TasksCountOrderingFilter(BaseFilterBackend):
#     def filter_queryset(self, request, queryset, view):
#         ordering = request.query_params.get('ordering', '')
#         if not ordering.lstrip('-') == 'tasks__count':
#             return queryset
#
#         return queryset.annotate(Count('tasks')).order_by('')
#
#         asc_desc = "-" if ordering.startswith("-") else ""
#         ordering_params = ["{}{}".format(asc_desc, param) for param in ["created_year", "id"]]
#         return queryset.annotate(created_year=TruncYear("created")).order_by(*ordering_params)
