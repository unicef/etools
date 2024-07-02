from django.contrib import admin
from django.contrib.contenttypes.admin import GenericStackedInline
from django.urls import reverse

from unicef_snapshot.admin import ActivityInline, SnapshotModelAdmin

from etools.applications.action_points.models import ActionPoint, ActionPointComment


class CommentInline(GenericStackedInline):
    model = ActionPointComment
    ct_field = "content_type"
    ct_fk_field = "object_pk"
    fields = ["user", "comment", "submit_date"]
    readonly_fields = ["user", "comment", "submit_date"]
    extra = 0
    can_delete = False
    can_add = False

    def view_on_site(self, obj):
        return reverse('admin:%s_%s_change' %
                       ('django_comments', 'comment'),
                       args=(obj.pk,),
                       current_app=self.admin_site.name)

    def has_add_permission(self, request, obj=None):
        return False


class ActionPointAdmin(SnapshotModelAdmin):
    list_display = ('reference_number', 'author', 'assigned_to', 'status', 'date_of_completion')
    list_filter = ('status', )
    readonly_fields = ('status', )
    search_fields = ('author__email', 'assigned_to__email', 'reference_number')
    inlines = (CommentInline, ActivityInline, )
    raw_id_fields = ('section', 'office', 'location', 'cp_output', 'partner', 'intervention', 'tpm_activity',
                     'psea_assessment', 'travel_activity', 'engagement', 'author', 'assigned_by', 'assigned_to',
                     'monitoring_activity')


admin.site.register(ActionPoint, ActionPointAdmin)
