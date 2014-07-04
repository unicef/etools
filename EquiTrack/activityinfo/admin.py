__author__ = 'jcranwellward'

from django.contrib import admin

from . import models


class DatabaseAdmin(admin.ModelAdmin):
    readonly_fields = (
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


class PartnerAdmin(admin.ModelAdmin):
    readonly_fields = (
        'ai_id',
        'name',
        'full_name',
        'database'
    )
    list_display = (
        'ai_id',
        'name',
        'full_name',
        'database'
    )


class AttributeGroupInlineAdmin(admin.TabularInline):
    can_delete = False
    model = models.AttributeGroup
    extra = 0
    fields = (
        'ai_id',
        'name',
        'multiple_allowed',
        'mandatory',
        'choices',
    )
    readonly_fields = (
        'ai_id',
        'name',
        'multiple_allowed',
        'mandatory',
        'choices',
    )

    def choices(self, obj):
        return ", ".join(
            [
                '{} ({})'.format(
                    attribute.name,
                    attribute.ai_id
                )
                for attribute
                in obj.attribute_set.all()
            ]
        )

    def has_add_permission(self, request):
        return False


class IndicatorInlineAdmin(admin.TabularInline):
    can_delete = False
    model = models.Indicator
    extra = 0
    fields = (
        'ai_id',
        'name',
        'units',
    )
    readonly_fields = (
        'ai_id',
        'name',
        'units',
    )

    def has_add_permission(self, request):
        return False


class ActivityAdmin(admin.ModelAdmin):
    inlines = [
        AttributeGroupInlineAdmin,
        IndicatorInlineAdmin,
    ]
    list_display = (
        'name',
        'location_type',
    )
    readonly_fields = (
        'ai_id',
        'name',
        'database',
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


class PartnerReportAdmin(admin.ModelAdmin):
    list_filter = (
        'pca',
        'indicator',
        'ai_partner',
        'ai_indicator',
        'location',
        'month',
    )
    list_display = (
        'pca',
        'indicator',
        'ai_partner',
        'ai_indicator',
        'location',
        'month',
        'indicator_value',
    )
    readonly_fields = (
        'pca',
        'indicator',
        'ai_partner',
        'ai_indicator',
        'location',
        'month',
        'indicator_value',
    )


admin.site.register(models.Database, DatabaseAdmin)
admin.site.register(models.Partner, PartnerAdmin)
admin.site.register(models.Activity, ActivityAdmin)
admin.site.register(models.Indicator, IndicatorAdmin)
admin.site.register(models.PartnerReport, PartnerReportAdmin)

