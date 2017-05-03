from __future__ import unicode_literals

from django.contrib import admin

from publics import models


class DSARateAdmin(admin.ModelAdmin):
    search_fields = ('region__area_name', 'region__country__name')
    list_filter = ('region__country__name',)


admin.site.register(models.TravelAgent)
admin.site.register(models.TravelExpenseType)
admin.site.register(models.Currency)
admin.site.register(models.ExchangeRate)
admin.site.register(models.AirlineCompany)
admin.site.register(models.BusinessRegion)
admin.site.register(models.BusinessArea)
admin.site.register(models.WBS)
admin.site.register(models.Grant)
admin.site.register(models.Fund)
admin.site.register(models.Country)
admin.site.register(models.DSARegion)
admin.site.register(models.DSARate, DSARateAdmin)
