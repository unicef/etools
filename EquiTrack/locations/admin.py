__author__ = 'jcranwellward'

from django.contrib.gis import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from import_export import resources
from import_export.admin import ImportExportMixin

from . import models


class LocationResource(resources.ModelResource):

    class Meta:
        model = models.Location


class UserResource(resources.ModelResource):

    class Meta:
        model = User


class UserAdminPlus(ImportExportMixin, UserAdmin):
    resource_class = UserResource


class LocationAdmin(ImportExportMixin, admin.GeoModelAdmin):
    resource_class = LocationResource
    fields = (
        'name',
        'gateway',
        'p_code',
        'point'
    )
    list_display = (
        'name',
        'gateway',
        'p_code',
        'locality',
    )
    search_fields = ('name', 'p_code',)
    list_filter = ('gateway', 'locality',)


class LocalityAdmin(admin.GeoModelAdmin):
    list_display = (
        'name',
        'region',
    )
    search_fields = ('name', 'cas_code')
    list_filter = ('region', 'cas_code')


admin.site.unregister(User)
admin.site.register(User, UserAdminPlus)
admin.site.register(models.Governorate, admin.GeoModelAdmin)
admin.site.register(models.Region, admin.GeoModelAdmin)
admin.site.register(models.Locality, LocalityAdmin)
admin.site.register(models.Location, LocationAdmin)
admin.site.register(models.GatewayType)
