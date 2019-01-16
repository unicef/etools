from django.contrib import admin

from etools.applications.action_points.admin import ActionPointAdmin
from etools.applications.publics.admin import AdminListMixin
from etools.applications.t2f import models
from etools.applications.t2f.models import T2FActionPoint


@admin.register(models.Travel)
class TravelAdmin(admin.ModelAdmin):
    list_filter = (
        'status',
        'traveler',
        'section'
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
        'section'
    )
    readonly_fields = (
        'status',
    )
    raw_id_fields = (
        'traveler',
        'supervisor'
    )


@admin.register(models.TravelActivity)
class TravelActivityAdmin(admin.ModelAdmin):
    list_filter = (
        'travel_type',
        'partner',
        'date',
        'travels'
    )
    search_fields = (
        'primary_traveler__first_name',
        'primary_traveler__last_name',
    )
    list_display = (
        'primary_traveler',
        'travel_type',
        'date'
    )
    raw_id_fields = (
        'primary_traveler',
    )


@admin.register(models.ItineraryItem)
class ItineraryItemAdmin(admin.ModelAdmin):
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


@admin.register(models.Expense)
class ExpenseAdmin(AdminListMixin, admin.ModelAdmin):
    raw_id_fields = (
        'travel',
    )


@admin.register(models.Deduction)
class DeductionAdmin(AdminListMixin, admin.ModelAdmin):
    raw_id_fields = (
        'travel',
    )


@admin.register(models.CostAssignment)
class CostAssignmentAdmin(AdminListMixin, admin.ModelAdmin):
    raw_id_fields = (
        'travel',
    )


@admin.register(models.TravelAttachment)
class TravelAttachmentAdmin(AdminListMixin, admin.ModelAdmin):
    pass


@admin.register(T2FActionPoint)
class T2FActionPointAdmin(ActionPointAdmin):
    pass
