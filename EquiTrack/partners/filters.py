from rest_framework.filters import BaseFilterBackend


class PartnerScopeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.parser_context['kwargs'] and 'partner_pk' in request.parser_context['kwargs']:
            return queryset.filter(partner__pk=request.parser_context['kwargs']['partner_pk'])
        return queryset
