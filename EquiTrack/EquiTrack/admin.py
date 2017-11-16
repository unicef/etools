from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from snapshot.models import Activity
from snapshot.utils import create_dict_with_relations, create_snapshot


class SnapshotModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        pre_save = None
        if obj is not None:
            if hasattr(obj, "pk") and obj.pk is not None:
                pre_save = obj.__class__.objects.get(pk=obj.pk)
        pre_save = create_dict_with_relations(pre_save)
        super(SnapshotModelAdmin, self).save_model(request, obj, form, change)
        create_snapshot(obj, pre_save, request.user)


class ActivityInline(GenericTabularInline):
    model = Activity
    ct_field = "target_content_type"
    ct_fk_field = "target_object_id"
    fields = ["action", "by_user_display", "change", "created"]
    readonly_fields = [
        "action",
        "by_user_display",
        "change",
        "created",
    ]
    extra = 0
    can_delete = False
    can_add = False

    def has_add_permission(self, request, obj=None):
        return False
