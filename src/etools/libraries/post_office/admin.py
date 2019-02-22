from django.contrib import admin

from post_office.admin import LogAdmin
from post_office.models import Log


class EtoolsPostOfficeLogAdmin(LogAdmin):

    def has_add_permission(self, request):
        return False


admin.site.unregister(Log)
admin.site.register(Log, EtoolsPostOfficeLogAdmin)
