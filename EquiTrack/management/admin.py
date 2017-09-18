from django.contrib import admin
from . import models as app_models


@admin.register(app_models.FlaggedIssue)
class FlaggedIssueAdmin(admin.ModelAdmin):
    list_display = ['content_object', 'issue_category', 'issue_id', 'issue_status', 'message']
    list_filter = ['issue_category', 'issue_id', 'issue_status']
    search_fields = ['message',]
