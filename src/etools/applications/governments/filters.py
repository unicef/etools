from rest_framework.filters import BaseFilterBackend


class PartnerNameOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get('ordering', '')
        if 'partner_name' in ordering:
            if '-' in ordering:
                return queryset.order_by('-partner__organization__name')
            return queryset.order_by('partner__organization__name')
        return queryset
