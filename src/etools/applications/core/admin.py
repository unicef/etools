from django.contrib import admin
from django.contrib.sites.models import Site

from etools.applications.core.models import Domain
from etools.libraries.djangolib.admin import RestrictedEditAdmin


@admin.register(Domain)
class DomainAdmin(RestrictedEditAdmin):
    pass


admin.site.unregister(Site)
admin.site.register(Site, RestrictedEditAdmin)
