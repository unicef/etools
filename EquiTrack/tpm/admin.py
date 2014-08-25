__author__ = 'jcranwellward'

from django.contrib import admin
from django.contrib.contenttypes.generic import GenericTabularInline

from reversion import VersionAdmin

from trips.models import FileAttachment
from partners.models import GwPCALocation
from .models import TPMVisit


class FileAttachmentInlineAdmin(GenericTabularInline):
    model = FileAttachment


class TPMVisitAdmin(VersionAdmin):
    list_display = (
        'status',
        'pca',
        'sectors',
        'location',
        'tentative_date',
        'completed_date'
    )
    readonly_fields = (
        'pca',
        'location',
        'unicef_manager',
        'partner_manager',
    )
    inlines = (
        FileAttachmentInlineAdmin,
    )

    def sectors(self, obj):
        return obj.pca.sectors

    def unicef_manager(self, obj):
        return u'{} {} ({})'.format(
            obj.pca.unicef_mng_first_name,
            obj.pca.unicef_mng_last_name,
            obj.pca.unicef_mng_email
        )

    def partner_manager(self, obj):
        return u'{} {} ({})'.format(
            obj.pca.partner_mng_first_name,
            obj.pca.partner_mng_last_name,
            obj.pca.partner_mng_email
        )


class TPMLocationsAdmin(admin.ModelAdmin):

    list_display = (
        'governorate',
        'region',
        'locality',
        'location',
        'view_location',
        'tpm_visit',
    )
    list_filter = (
        'governorate',
        'region',
        'locality',
        'location',
    )
    search_fields = (
        'governorate',
        'region',
        'locality',
        'location',
    )
    readonly_fields = (
        'view_location',
    )
    list_editable = (
        'tpm_visit',
    )


admin.site.register(TPMVisit, TPMVisitAdmin)
admin.site.register(GwPCALocation, TPMLocationsAdmin)