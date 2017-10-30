from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.contrib import admin

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
