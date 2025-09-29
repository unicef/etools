from django.contrib import admin

from unicef_vision.admin import VisionLoggerAdmin

from etools.applications.vision.models import VisionSyncLog


@admin.register(VisionSyncLog)
class VisionSyncLogAdmin(VisionLoggerAdmin):

    change_form_template = 'admin/vision/vision_log/change_form.html'

    list_filter = VisionLoggerAdmin.list_filter + ('country',)
    list_display = VisionLoggerAdmin.list_display + ('country',)
    readonly_fields = VisionLoggerAdmin.readonly_fields + ('country',)

    actions = None

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm('vision.view_visionsynclog')

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def has_add_permission(self, request):
        return request.user.has_perm('vision.add_visionsynclog')

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('vision.change_visionsynclog')

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm('vision.delete_visionsynclog')

    def get_model_perms(self, request):
        # Advertise permissions to admin index so the model is visible with view-only access
        perms = super().get_model_perms(request)
        perms['view'] = self.has_view_permission(request)
        perms['add'] = self.has_add_permission(request)
        perms['change'] = self.has_change_permission(request)
        perms['delete'] = self.has_delete_permission(request)
        return perms
