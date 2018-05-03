from django.contrib import admin

from etools.applications.funds.models import (Donor, FundsCommitmentHeader, FundsCommitmentItem,
                                              FundsReservationHeader, FundsReservationItem, Grant,)


class GrantAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_filter = ('donor',)


class FRAdmin(admin.ModelAdmin):
    search_fields = ('fr_number',)


class FRAdminLi(admin.ModelAdmin):
    search_fields = ('fr_ref_number',)


admin.site.register(Grant, GrantAdmin)
admin.site.register(Donor)
admin.site.register(FundsReservationHeader, FRAdmin)
admin.site.register(FundsReservationItem, FRAdminLi)
admin.site.register(FundsCommitmentHeader)
admin.site.register(FundsCommitmentItem)
