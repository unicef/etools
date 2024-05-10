from django.contrib import admin

from etools.applications.eface.models import EFaceForm, FormActivity


class FormActivityAdmin(admin.StackedInline):
    model = FormActivity


@admin.register(EFaceForm)
class EFaceFormAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'request_type', 'status')
    list_filter = ('status',)
    search_fields = ('reference_number',)
