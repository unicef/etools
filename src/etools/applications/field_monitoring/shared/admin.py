from django.contrib import admin
from ordered_model.admin import OrderedModelAdmin

from etools.applications.field_monitoring.shared.models import Method


@admin.register(Method)
class MethodAdmin(OrderedModelAdmin):
    list_display = ('name', 'is_types_applicable')
