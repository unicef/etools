__author__ = 'jcranwellward'

from django.contrib import admin

from . import models


class GrantAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_filter = ('donor',)


admin.site.register(models.Grant, GrantAdmin)
admin.site.register(models.Donor)
