from django.db.models.query_utils import Q

from rest_framework.filters import BaseFilterBackend

from partners.serializers.v1 import PartnershipExportFilterSerializer, AgreementExportFilterSerializer


class PartnerScopeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.parser_context['kwargs'] and 'partner_pk' in request.parser_context['kwargs']:
            return queryset.filter(partner__pk=request.parser_context['kwargs']['partner_pk'])
        return queryset


class PartnerOrganizationExportFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        parameter_serializer = PartnershipExportFilterSerializer(data=request.GET)
        parameter_serializer.is_valid(raise_exception=True)

        parameters = parameter_serializer.data

        q = Q()
        search_str = parameters.get('search')
        if search_str:
            search_q = Q(
                Q(name__istartswith=search_str) |
                Q(short_name__istartswith=search_str) |
                Q(vendor_number__istartswith=search_str)
            )
            q &= search_q

        partner_type = parameters.get('partner_type')
        if partner_type:
            q &= Q(partner_type=partner_type)

        cso_type = parameters.get('cso_type')
        if cso_type:
            q &= Q(cso_type=cso_type)

        risk_rating = parameters.get('risk_rating')
        if risk_rating:
            q &= Q(rating=risk_rating)

        flag = parameters.get('flagged')
        if flag == PartnershipExportFilterSerializer.MARKED_FOR_DELETION:
            q &= Q(deleted_flag=True)

        show_hidden = parameters.get('show_hidden')
        if not show_hidden:
            q &= Q(hidden=False)

        return queryset.filter(q)


class AgreementExportFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        parameter_serializer = AgreementExportFilterSerializer(data=request.GET)
        parameter_serializer.is_valid(raise_exception=True)

        parameters = parameter_serializer.data

        q = Q()
        search_str = parameters.get('search')
        if search_str:
            search_q = Q(
                Q(partner__name__istartswith=search_str) |
                Q(short_name__istartswith=search_str) |
                Q(partner__vendor_number__istartswith=search_str)
            )
            q &= search_q

        agreement_type = parameters.get('agreement_type')
        if agreement_type:
            q &= Q(agreement_type=agreement_type)

        starts_after = parameters.get('starts_after')
        if starts_after:
            q &= Q(start_date__gte=starts_after)

        ends_before = parameters.get('ends_before')
        if ends_before:
            q &= Q(end_date__lte=ends_before)

        return queryset.filter(q)
