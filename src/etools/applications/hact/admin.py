from django.contrib import admin

from etools.applications.hact.models import AggregateHact, HactHistory
from etools.libraries.djangolib.admin import RestrictedEditAdmin


@admin.register(HactHistory)
class HactHistoryAdmin(RestrictedEditAdmin):
    list_filter = ('year', )
    search_fields = ('partner__organization__name', 'year')
    list_display = ('partner', 'year')


@admin.register(AggregateHact)
class AggregateHactAdmin(RestrictedEditAdmin):
    list_filter = (
        'year',
    )
    readonly_fields = ('year', 'partner_values')
