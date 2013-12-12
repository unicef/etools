__author__ = 'jcranwellward'

from django.contrib.gis import admin

from . import models


class LocationAdmin(admin.GeoModelAdmin):

    fields = (
        'name',
        'p_code',
        'point'
    )
    list_display = ('name', 'p_code', 'locality',)
    search_fields = ('name', 'p_code',)


admin.site.register(models.Governorate, admin.GeoModelAdmin)
admin.site.register(models.Region, admin.GeoModelAdmin)
admin.site.register(models.Locality, admin.GeoModelAdmin)
admin.site.register(models.Location, LocationAdmin)
