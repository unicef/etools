from django.contrib import admin

from etools.applications.core.models import Domain


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    pass
