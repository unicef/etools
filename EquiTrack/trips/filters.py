__author__ = 'jcranwellward'

from django.contrib import admin
from django.db.models import Q

from partners.models import PartnerOrganization


class PartnerFilter(admin.SimpleListFilter):

    title = 'Partner'
    parameter_name = 'partner'

    def lookups(self, request, model_admin):

        return [
            (partner.id, partner.name) for partner in PartnerOrganization.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            partner = PartnerOrganization.objects.get(pk=self.value())
            return queryset.filter(partner__containts=[partner])
        return queryset


class TripReportFilter(admin.SimpleListFilter):

    title = 'Report'
    parameter_name = 'report'

    def lookups(self, request, model_admin):

        return [
            ('Yes', 'Completed'),
            ('No', 'Not-Completed'),
        ]

    def queryset(self, request, queryset):

        if self.value():
            is_null = Q(main_observations='')
            return queryset.filter(is_null if self.value() == 'No' else ~is_null)
        return queryset