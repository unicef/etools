from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib import admin
from django.contrib.contenttypes import admin as ct_admin
from ordered_model.admin import OrderedModelAdmin

from attachments import models as app_models


@admin.register(app_models.FileType)
class FileTypeAdmin(OrderedModelAdmin):
    list_display = ['label', 'name', 'code', 'move_up_down_links']
    list_filter = ['code', ]
    search_fields = ['name', 'label']


@admin.register(app_models.Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['file_type', 'file', 'content_object', ]
    list_filter = ['file_type', ]


class AttachmentInline(ct_admin.GenericTabularInline):
    model = app_models.Attachment
    extra = 0
    fields = ('file', 'hyperlink', )


class AttachmentSingleInline(AttachmentInline):
    def has_add_permission(self, request):
        return False
