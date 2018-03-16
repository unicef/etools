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
    list_display = ('get_related_module', 'related_object', 'author', 'assigned_to', 'status', 'date_of_complete')
    list_filter = ('status', )
    search_fields = ('author__email', 'assigned_to__email')
    inlines = (CommentInline, ActivityInline, )

    def get_related_module(self, obj):
        return obj.get_related_module()
    get_related_module.short_description = 'Related Module'


admin.site.register(ActionPoint, ActionPointAdmin)
