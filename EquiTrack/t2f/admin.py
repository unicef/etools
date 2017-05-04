from __future__ import unicode_literals

from django.contrib import admin

from t2f import models


class TravelAdmin(admin.ModelAdmin):
    model = models.Travel
    list_filter = (
        'status',
        'traveler',
    )
    search_fields = (
        'reference_number',
    )
    list_display = (
        'reference_number',
        'traveler',
        'status',
        'start_date',
        'end_date',
    )
    readonly_fields = (
        'status',
    )


class TravelActivityAdmin(admin.ModelAdmin):
    model = models.TravelActivity
    list_filter = (
        'travel_type',
        'partner',
        'date',
        'travels'
    )
    search_fields = (
        'primary_traveler',
    )
    list_display = (
        'primary_traveler',
        'travel_type',
        'date'
    )


class ItineraryItemAdmin(admin.ModelAdmin):
    model = models.IteneraryItem
    list_filter = (
        'travel',
        'departure_date',
        'arrival_date',
        'origin',
        'destination'
    )
    search_fields = (
        'travel__reference_number',
    )
    list_display = (
        'travel',
        'departure_date',
        'arrival_date',
        'origin',
        'destination'
    )


class ActionPointAdmin(admin.ModelAdmin):
    model = models.ActionPoint
    list_filter = (
        'travel',
        'status',
    )
    search_fields = (
        'action_point_number',
        'travel__reference_number'
    )
    list_display = (
        'action_point_number',
        'travel',
        'description',
        'status',
        'completed_at',
    )

admin.site.register(models.TravelActivity, TravelActivityAdmin)
admin.site.register(models.Travel, TravelAdmin)
admin.site.register(models.IteneraryItem, ItineraryItemAdmin)
admin.site.register(models.ActionPoint, ActionPointAdmin)
