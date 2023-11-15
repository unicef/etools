from django.conf import settings
from django.contrib import admin
from django.db.models import ForeignKey, ManyToManyField, OneToOneField

from etools.libraries.djangolib.models import EPOCH_ZERO


class AdminListMixin:
    exclude_fields = ['id', 'deleted_at']
    custom_fields = ['is_deleted']

    def __init__(self, model, admin_site):
        """
        Gather all the fields from model meta expect fields in 'exclude_fields'.
        Add all fields listed in 'custom_fields'. Those can be admin method, model methods etc.
        """
        self.list_display = [field.name for field in model._meta.fields if field.name not in self.exclude_fields]
        self.list_display += self.custom_fields
        self.search_fields = [field.name for field in model._meta.fields if isinstance(
            not field, (OneToOneField, ForeignKey, ManyToManyField)) and field.name not in self.exclude_fields]

        super().__init__(model, admin_site)

    def is_deleted(self, obj):
        """
        Display a deleted indicator on the admin page (green/red tick).
        """
        if hasattr(obj, "deleted_at"):
            return obj.deleted_at == EPOCH_ZERO

    is_deleted.short_description = 'Deleted'
    is_deleted.boolean = True


class RestrictedEditAdminMixin:
    def has_add_permission(self, request, obj=None):
        if not settings.RESTRICTED_ADMIN:
            return True
        return request.user.email in settings.ADMIN_EDIT_EMAILS

    def has_change_permission(self, request, obj=None):
        if not settings.RESTRICTED_ADMIN:
            return True
        return request.user.email in settings.ADMIN_EDIT_EMAILS

    def has_delete_permission(self, request, obj=None):
        if not settings.RESTRICTED_ADMIN:
            return True
        return request.user.email in settings.ADMIN_EDIT_EMAILS


class RestrictedEditAdmin(RestrictedEditAdminMixin, admin.ModelAdmin):
    pass
