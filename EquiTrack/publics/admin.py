from __future__ import unicode_literals

from django.contrib import admin

from publics import models

admin.site.register(models.Grant)
admin.site.register(models.Fund)
admin.site.register(models.WBS)
admin.site.register(models.TravelExpenseType)
admin.site.register(models.Currency)
admin.site.register(models.DSARegion)
admin.site.register(models.AirlineCompany)
