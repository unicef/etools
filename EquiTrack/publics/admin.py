from __future__ import unicode_literals

from django.contrib import admin

from publics import models
from publics.mixins import AdminListMixin


class TravelAgentAdmin(AdminListMixin, admin.ModelAdmin):
    pass


class TravelExpenseTypeAdmin(AdminListMixin, admin.ModelAdmin):
    pass


class CurrencyAdmin(AdminListMixin, admin.ModelAdmin):
    pass


class ExchangeRateAdmin(AdminListMixin, admin.ModelAdmin):
    pass


class AirlineCompanyAdmin(AdminListMixin, admin.ModelAdmin):
    pass


class BusinessRegionAdmin(AdminListMixin, admin.ModelAdmin):
    pass


class BusinessAreaAdmin(AdminListMixin, admin.ModelAdmin):
    pass


class WBSAdmin(AdminListMixin, admin.ModelAdmin):
    pass


class GrantAdmin(AdminListMixin, admin.ModelAdmin):
    pass


class FundAdmin(AdminListMixin, admin.ModelAdmin):
    pass


class CountryAdmin(AdminListMixin, admin.ModelAdmin):
    pass


class DSARegionAdmin(AdminListMixin, admin.ModelAdmin):
    pass


admin.site.register(models.TravelAgent, TravelAgentAdmin)
admin.site.register(models.TravelExpenseType, TravelExpenseTypeAdmin)
admin.site.register(models.Currency, CurrencyAdmin)
admin.site.register(models.ExchangeRate, ExchangeRateAdmin)
admin.site.register(models.AirlineCompany, AirlineCompanyAdmin)
admin.site.register(models.BusinessRegion, BusinessAreaAdmin)
admin.site.register(models.BusinessArea, BusinessAreaAdmin)
admin.site.register(models.WBS, WBSAdmin)
admin.site.register(models.Grant, GrantAdmin)
admin.site.register(models.Fund, FundAdmin)
admin.site.register(models.Country, CountryAdmin)
admin.site.register(models.DSARegion, DSARegionAdmin)
