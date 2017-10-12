from django.contrib import admin
from . import models as app_models


@admin.register(app_models.IssueCheckConfig)
class IssueCheckConfigAdmin(admin.ModelAdmin):
    list_display = ['check_id', 'is_active']
    list_filter = ['is_active']
