from django.contrib import admin

from etools.applications.attachments.models import AttachmentFlat


@admin.register(AttachmentFlat)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = [
        'partner',
        'partner_type',
        'vendor_number',
        'pd_ssfa',
        'pd_ssfa_number',
        'agreement_reference_number',
        'file_type',
        'file_link',
        'filename',
        'uploaded_by',
        'ip_address',
    ]
    list_filter = ['file_type', 'partner', ]
