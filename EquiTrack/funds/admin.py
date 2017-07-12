from django.contrib import admin

from . import models


class GrantAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_filter = ('donor',)


admin.site.register(models.Grant, GrantAdmin)
admin.site.register(models.Donor)
admin.site.register(models.FundsReservationHeader)
admin.site.register(models.FundsReservationItem)
admin.site.register(models.FundsCommitmentHeader)
admin.site.register(models.FundsCommitmentItem)
