from django.contrib import admin

from etools.applications.publics import models
from etools.libraries.djangolib.admin import AdminListMixin


class DSARateAdmin(admin.ModelAdmin):
    search_fields = ('region__area_name', 'region__country__name')
    list_filter = ('region__country__name',)


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


class CountryAdmin(AdminListMixin, admin.ModelAdmin):
    pass


class DSARegionAdmin(AdminListMixin, admin.ModelAdmin):
    pass


admin.site.register(models.DSARate, DSARateAdmin)
admin.site.register(models.TravelAgent, TravelAgentAdmin)
admin.site.register(models.TravelExpenseType, TravelExpenseTypeAdmin)
admin.site.register(models.Currency, CurrencyAdmin)
admin.site.register(models.ExchangeRate, ExchangeRateAdmin)
admin.site.register(models.AirlineCompany, AirlineCompanyAdmin)
admin.site.register(models.BusinessRegion, BusinessAreaAdmin)
admin.site.register(models.BusinessArea, BusinessAreaAdmin)
admin.site.register(models.Country, CountryAdmin)
admin.site.register(models.DSARegion, DSARegionAdmin)
