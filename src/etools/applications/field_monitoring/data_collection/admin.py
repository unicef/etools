from django.contrib import admin

from etools.applications.field_monitoring.data_collection.models import StartedMethod


@admin.register(StartedMethod)
class StartedMethodAdmin(admin.ModelAdmin):
    list_display = ('visit', 'method', 'method_type', 'author', 'status',)
    list_filter = ('status',)
