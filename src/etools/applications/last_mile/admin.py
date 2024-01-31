from django.contrib import admin

from etools.applications.last_mile.models import PointOfInterest, PointOfInterestType


@admin.register(PointOfInterest)
class PointOfInterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'poi_type')
    list_select_related = ('parent',)
    list_filter = ('private', 'is_active')
    search_fields = ('name', )
    raw_id_fields = ('partner_organization',)


admin.site.register(PointOfInterestType)
