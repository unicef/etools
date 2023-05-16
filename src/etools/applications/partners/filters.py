from django.shortcuts import get_object_or_404

from rest_framework.filters import BaseFilterBackend

from etools.applications.partners.models import PartnerOrganization


class PartnerScopeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.parser_context['kwargs'] and 'partner_pk' in request.parser_context['kwargs']:
            partner = get_object_or_404(PartnerOrganization, pk=request.parser_context['kwargs']['partner_pk'])
            return partner.all_staff_members
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


class ShowAmendmentsFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if 'show_amendments' in request.query_params:
            return queryset
        return queryset.filter(in_amendment=False)


class InterventionEditableByFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        editable_by = request.query_params.get('editable_by', None)
        if editable_by is None:
            return queryset

        return queryset.filter(**{
            'unicef': {'unicef_court': True},
            'partner': {'unicef_court': False, 'date_sent_to_partner__isnull': False},
        }.get(editable_by, {}))
