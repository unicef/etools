from django.db import connection

from rest_framework.filters import BaseFilterBackend
from rest_framework.generics import get_object_or_404

from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.mixins import PARTNER_ACTIVE_GROUPS


class PartnerNameOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get('ordering', '')
        if 'partner_name' in ordering:
            if '-' in ordering:
                return queryset.order_by('-partner__organization__name')
            return queryset.order_by('partner__organization__name')
        return queryset


class PartnerScopeFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.parser_context['kwargs'] and 'partner_pk' in request.parser_context['kwargs']:
            partner = get_object_or_404(PartnerOrganization, pk=request.parser_context['kwargs']['partner_pk'])
            return queryset.filter(
                realms__country=connection.tenant,
                realms__organization=partner.organization,
                realms__group__name__in=PARTNER_ACTIVE_GROUPS,
            ).distinct()
        return queryset


class GDDEditableByFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        editable_by = request.query_params.get('editable_by', None)
        if editable_by is None:
            return queryset

        return queryset.filter(**{
            'unicef': {'unicef_court': True},
            'partner': {'unicef_court': False, 'date_sent_to_partner__isnull': False},
        }.get(editable_by, {}))


class ShowAmendmentsFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if 'show_amendments' in request.query_params:
            return queryset
        return queryset.filter(in_amendment=False)


class GDDFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.parser_context['kwargs'] and 'gdd_pk' in request.parser_context['kwargs']:
            return queryset.filter(gdd__pk=request.parser_context['kwargs']['gdd_pk'])
        return queryset