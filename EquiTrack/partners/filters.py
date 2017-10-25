from rest_framework.filters import BaseFilterBackend


class PartnerScopeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.parser_context['kwargs'] and 'partner_pk' in request.parser_context['kwargs']:
            return queryset.filter(partner__pk=request.parser_context['kwargs']['partner_pk'])
        return queryset


class InterventionFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.parser_context['kwargs'] and 'intervention_pk' in request.parser_context['kwargs']:
            return queryset.filter(intervention__pk=request.parser_context['kwargs']['intervention_pk'])
        return queryset


class InterventionResultLinkFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.parser_context['kwargs'] and 'result_link_pk' in request.parser_context['kwargs']:
            return queryset.filter(result_link__pk=request.parser_context['kwargs']['result_link_pk'])
        return queryset


class AppliedIndicatorsFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.parser_context['kwargs'] and 'lower_result_pk' in request.parser_context['kwargs']:
            return queryset.filter(lower_result__pk=request.parser_context['kwargs']['lower_result_pk'])
        return queryset
