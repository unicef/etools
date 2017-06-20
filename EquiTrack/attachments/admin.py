from django.contrib import admin
from ordered_model.admin import OrderedModelAdmin

from . import models as app_models


@admin.register(app_models.FileType)
class FileTypeAdmin(OrderedModelAdmin):
    list_display = ['name', 'code', 'move_up_down_links']
    list_filter = ['code', ]
    search_fields = ['name', ]


@admin.register(app_models.Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['file_type', 'file', 'object', ]
    list_filter = ['file_type', ]
