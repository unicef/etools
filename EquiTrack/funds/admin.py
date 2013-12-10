__author__ = 'jcranwellward'

from django.contrib import admin

from . import models


admin.site.register(models.Grant)
admin.site.register(models.Donor)