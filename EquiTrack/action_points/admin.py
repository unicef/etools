from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib import admin
from django.contrib.contenttypes.admin import GenericStackedInline

from django_comments.models import Comment

from EquiTrack.admin import SnapshotModelAdmin, ActivityInline
from action_points.models import ActionPoint


class CommentInline(GenericStackedInline):
    model = Comment
    ct_field = "content_type"
    ct_fk_field = "object_pk"
    fields = ["user", "comment", "submit_date"]
    readonly_fields = ["user", "comment", "submit_date"]
    extra = 0
    can_delete = False
    can_add = False

    def has_add_permission(self, request, obj=None):
        return False


class ActionPointAdmin(SnapshotModelAdmin):
    list_display = ('author', 'assigned_to', 'status', 'date_of_completion')
    list_filter = ('status', )
    search_fields = ('author__email', 'assigned_to__email')
    inlines = (CommentInline, ActivityInline, )
    readonly_fields = ('status', )


admin.site.register(ActionPoint, ActionPointAdmin)
