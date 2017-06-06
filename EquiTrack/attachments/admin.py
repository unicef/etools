from django.contrib import admin


from . import models as app_models


@admin.register(app_models.FileType)
class FileTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    list_filter = ['code', ]
    search_fields = ['name', ]


@admin.register(app_models.Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['file_type', 'file', 'object', ]
    list_filter = ['file_type', ]
