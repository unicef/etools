from django.contrib import admin

from hact.models import HactHistory


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
