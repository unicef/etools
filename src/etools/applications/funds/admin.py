from django.contrib import admin

from etools.applications.funds.models import (
    Donor,
    FundsCommitmentHeader,
    FundsCommitmentItem,
    FundsReservationHeader,
    FundsReservationItem,
    Grant,
)
from etools.libraries.djangolib.admin import RestrictedEditAdmin


class GrantAdmin(RestrictedEditAdmin):
    search_fields = ('name',)
    list_filter = ('donor',)


class FRAdmin(RestrictedEditAdmin):
    search_fields = ('fr_number',)
    list_display = ('fr_number', 'vendor_code')
    list_filter = ('completed_flag', 'delegated')


class FRAdminLi(RestrictedEditAdmin):
    search_fields = ('fr_ref_number',)
    list_display = ('fr_ref_number', 'donor', 'donor_code', 'grant_number')


admin.site.register(Grant, GrantAdmin)
admin.site.register(Donor, RestrictedEditAdmin)
admin.site.register(FundsReservationHeader, FRAdmin)
admin.site.register(FundsReservationItem, FRAdminLi)
admin.site.register(FundsCommitmentHeader, RestrictedEditAdmin)
admin.site.register(FundsCommitmentItem, RestrictedEditAdmin)
