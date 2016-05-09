__author__ = 'jcranwellward'

from django.db import connection
from django.contrib import admin
from django.db.models import Q
from django.contrib.auth.models import User

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
            return queryset.filter(linkpartners_set__containts=[partner])
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


class UserStaffFliterMixin(object):

    def lookups(self, request, model_admin):
        return [
            (user.id, user)
            for user in User.objects.filter(is_staff=True).all()
        ]
    def queryset(self, request, queryset):

        if self.value():
            my_f = self.parameter_name + "__pk__exact"
            return queryset.filter(
                **{
                    my_f: self.value(),
                    'profile__country': connection.tenant,
                }
            )
        return queryset


class SupervisorFilter(UserStaffFliterMixin, admin.SimpleListFilter):

    title = 'Supervisor'
    parameter_name = 'supervisor'


class OwnerFilter(UserStaffFliterMixin, admin.SimpleListFilter):

    title = 'Traveller'
    parameter_name = 'owner'
