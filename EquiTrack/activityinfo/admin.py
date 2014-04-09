__author__ = 'jcranwellward'

from django.contrib import admin

from . import models


class DatabaseAdmin(admin.ModelAdmin):
    readonly_fields = (
        'name',
        'description',
        'country_name',
        'ai_country_id'
    )
    actions = [
        'import_data',
        'import_reports'
    ]

    def import_data(self, request, queryset):
        objects = 0
        for db in queryset:
            objects += db.import_data()
        self.message_user(
            request,
            "{} objects created.".format(objects)
        )

    def import_reports(self, request, queryset):
        reports = 0
        for db in queryset:
            reports += db.import_reports()
        self.message_user(
            request,
            "{} reports created.".format(reports)
        )


class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'location_type',
    )


class IndicatorAdmin(admin.ModelAdmin):
    search_fields = (
        'ai_id',
    )
    list_filter = (
        'category',
    )
    list_display = (
        'ai_id',
        'activity',
        'name',
        'units',
        'category',
    )

class PartnerReportInlineAdmin(admin.TabularInline):
    model = models.PartnerReport
    readonly_fields = (
        'indicator',
        'indicator_value'
    )


admin.site.register(models.Database, DatabaseAdmin)
admin.site.register(models.Partner)
admin.site.register(models.Activity, ActivityAdmin)
admin.site.register(models.Indicator, IndicatorAdmin)

