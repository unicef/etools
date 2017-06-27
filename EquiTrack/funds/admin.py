__author__ = 'jcranwellward'

from django.contrib import admin

from . import models


class GrantAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_filter = ('donor',)


class FRAdmin(admin.ModelAdmin):
    search_fields = ('fr_number',)

admin.site.register(models.Grant, GrantAdmin)
admin.site.register(models.Donor)
admin.site.register(models.FundsReservationHeader, FRAdmin)
admin.site.register(models.FundsReservationItem)
admin.site.register(models.FundsCommitmentHeader)
admin.site.register(models.FundsCommitmentItem)
