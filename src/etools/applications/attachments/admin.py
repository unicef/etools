
from django.contrib import admin

from ordered_model.admin import OrderedModelAdmin

from etools.applications.attachments import models as app_models


@admin.register(app_models.FileType)
class FileTypeAdmin(OrderedModelAdmin):
    list_display = ['label', 'name', 'code', 'move_up_down_links']
    list_filter = ['code', ]
    search_fields = ['name', 'label']


@admin.register(app_models.Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = [
        'file_type',
        'file',
        'modified',
        'uploaded_by',
    ]
    list_filter = ['file_type', ]
