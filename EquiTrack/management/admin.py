from django.contrib import admin
from . import models as app_models


@admin.register(app_models.FlaggedIssue)
class FlaggedIssueAdmin(admin.ModelAdmin):
    list_display = ['content_object', 'issue_category', 'issue_id', 'issue_status', 'date_created',
                    'date_updated', 'message']
    list_filter = ['issue_category', 'issue_id', 'issue_status', 'date_created', 'date_updated']
    search_fields = ['message']
