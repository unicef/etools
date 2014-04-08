__author__ = 'jcranwellward'

from django.contrib import admin

from . import models


admin.site.register(models.Database)
admin.site.register(models.Partner)
admin.site.register(models.Activity)
admin.site.register(models.Indicator)

