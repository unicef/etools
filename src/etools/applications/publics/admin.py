from django.contrib import admin

from etools.applications.publics import models
from etools.libraries.djangolib.admin import AdminListMixin, RestrictedEditAdmin


class DSARateAdmin(RestrictedEditAdmin):
    search_fields = ('region__area_name', 'region__country__name')
    list_filter = ('region__country__name',)


class DSARateUploadAdmin(RestrictedEditAdmin):
    list_display = (
        'id',
        'dsa_file',
        'status',
        'upload_date',
        'errors',
    )

    def get_form(self, request, obj=None, **kwargs):
        if not obj:
            self.readonly_fields = []
            self.exclude = (
                'id',
                'status',
                'upload_date',
                'errors',
            )
        else:
            self.readonly_fields = (
                'id',
                'dsa_file',
                'status',
                'upload_date',
                'errors',
            )
            self.exclude = (
                'errors',
            )
        return super().get_form(request, obj, **kwargs)

    def change_view(self, *args, **kwargs):
        extra_context = {}
        extra_context['show_save_and_continue'] = False
        extra_context['show_save_and_add_another'] = False
        extra_context['show_save'] = False
        return super().change_view(extra_context=extra_context, *args, **kwargs)


class TravelAgentAdmin(AdminListMixin, RestrictedEditAdmin):
    pass


class TravelExpenseTypeAdmin(AdminListMixin, RestrictedEditAdmin):
    pass


class CurrencyAdmin(AdminListMixin, RestrictedEditAdmin):
    pass


class ExchangeRateAdmin(AdminListMixin, RestrictedEditAdmin):
    pass


class AirlineCompanyAdmin(AdminListMixin, RestrictedEditAdmin):
    pass


class BusinessRegionAdmin(AdminListMixin, RestrictedEditAdmin):
    pass


class BusinessAreaAdmin(AdminListMixin, RestrictedEditAdmin):
    pass


class CountryAdmin(AdminListMixin, RestrictedEditAdmin):
    pass


class DSARegionAdmin(AdminListMixin, RestrictedEditAdmin):
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
