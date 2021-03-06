from django.contrib import admin
from django.contrib.contenttypes.admin import GenericStackedInline

from django_comments.models import Comment
from unicef_snapshot.admin import ActivityInline, SnapshotModelAdmin

from etools.applications.action_points.models import ActionPoint


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
    raw_id_fields = ('section', 'office', 'location', 'cp_output', 'partner', 'intervention', 'tpm_activity',
                     'psea_assessment', 'travel_activity', 'engagement', 'author', 'assigned_by', 'assigned_to')


admin.site.register(ActionPoint, ActionPointAdmin)
