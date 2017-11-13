from django.contrib import admin

from environment.models import IssueCheckConfig


@admin.register(IssueCheckConfig)
class IssueCheckConfigAdmin(admin.ModelAdmin):
    list_display = ['check_id', 'is_active']
    list_filter = ['is_active']
