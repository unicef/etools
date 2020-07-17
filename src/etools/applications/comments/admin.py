from django.contrib import admin

from etools.applications.comments.models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'state', 'related_to_description', 'text',)
    list_select_related = ('user',)
    list_filter = ('state',)
    search_fields = ('related_to_description', 'text',)
