
from django.contrib import admin

from etools.applications.hact.models import AggregateHact, HactHistory


@admin.register(HactHistory)
class HactHistoryAdmin(admin.ModelAdmin):
    list_filter = (
        'year',
    )
    search_fields = (
        'partner',
        'year'
    )
    list_display = (
        'partner',
        'year',
    )


@admin.register(AggregateHact)
class AggregateHactAdmin(admin.ModelAdmin):
    list_filter = (
        'year',
    )
