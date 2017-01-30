from __future__ import unicode_literals

from django.contrib import admin

from t2f import models


admin.site.register(models.TravelActivity)
admin.site.register(models.Travel)
admin.site.register(models.IteneraryItem)
