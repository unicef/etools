from django.contrib import admin

from etools.applications.last_mile import models


@admin.register(models.PointOfInterest)
class PointOfInterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'poi_type')
    list_select_related = ('parent',)
    list_filter = ('private', 'is_active')
    search_fields = ('name', )
    raw_id_fields = ('partner_organization',)


@admin.register(models.Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('sequence_number', 'partner_organization', 'status')
    list_select_related = ('partner_organization',)
    list_filter = ('status',)
    search_fields = ('sequence_number', )
    raw_id_fields = ('partner_organization', 'checked_in_by', 'checked_out_by')


admin.site.register(models.PointOfInterestType)
admin.site.register(models.Material)
admin.site.register(models.Item)
