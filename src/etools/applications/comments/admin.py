from django.contrib import admin

from etools.applications.comments.models import Comment
from etools.libraries.djangolib.admin import RestrictedEditAdmin


@admin.register(Comment)
class CommentAdmin(RestrictedEditAdmin):
    list_display = ('user', 'state', 'related_to_description', 'text',)
    list_select_related = ('user',)
    list_filter = ('state',)
    search_fields = ('related_to_description', 'text',)
