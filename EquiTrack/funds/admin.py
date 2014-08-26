__author__ = 'jcranwellward'

from django.contrib import admin

from import_export.admin import ImportExportModelAdmin

from . import models


admin.site.register(models.Grant, ImportExportModelAdmin)
admin.site.register(models.Donor, ImportExportModelAdmin)