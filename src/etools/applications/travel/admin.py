from django.contrib import admin

from etools.applications.travel.models import Activity, Report, Trip
from etools.libraries.djangolib.admin import RestrictedEditAdmin, RestrictedEditAdminMixin


class ActivityInline(RestrictedEditAdminMixin, admin.TabularInline):
    raw_id_fields = ["location", "partner"]
    model = Activity


class ReportInline(RestrictedEditAdminMixin, admin.TabularInline):
    model = Report


@admin.register(Trip)
class TripAdmin(RestrictedEditAdmin):
    list_display = (
        'reference_number',
        'status',
        'traveller',
        'start_date',
        'end_date',
    )
    list_filter = ('reference_number', 'status',)
    search_fields = ('reference_number', 'traveller__email',)
    raw_id_fields = ["traveller", "supervisor"]
    inlines = [
        ActivityInline,
        ReportInline,
    ]
