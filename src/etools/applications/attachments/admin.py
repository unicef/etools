from django.contrib import admin

from etools.applications.attachments.models import AttachmentFlat
from etools.libraries.djangolib.admin import RestrictedEditAdmin


@admin.register(AttachmentFlat)
class AttachmentAdmin(RestrictedEditAdmin):
    list_display = [
        'partner',
        'partner_type',
        'vendor_number',
        'pd_ssfa',
        'pd_ssfa_number',
        'agreement_reference_number',
        'source',
        'file_type',
        'file_link',
        'filename',
        'uploaded_by',
        'ip_address',
    ]
    list_filter = ['file_type', 'source', 'partner', ]
