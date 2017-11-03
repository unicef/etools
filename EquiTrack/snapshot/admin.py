from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.contrib import admin

from snapshot.models import Activity


class ActivityAdmin(admin.ModelAdmin):
    model = Activity
    readonly_fields = [
        'target_content_type',
        'target_object_id',
        'target',
        'action',
        'by_user_display',
        'data',
        'change',
        'created',
        'modified',
    ]
    list_display = (
        'target',
        'action',
        'by_user_display'
    )
    list_filter = (
        'action',
    )


admin.site.register(Activity, ActivityAdmin)
