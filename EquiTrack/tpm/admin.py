from django.contrib import admin

from reversion.admin import VersionAdmin
from import_export.admin import ExportMixin

from reports.models import Sector
from partners.models import PartnerOrganization
from tpm.models import TPMVisit
from tpm.exports import TPMResource


class SectorListFilter(admin.SimpleListFilter):

    title = 'Sector'
    parameter_name = 'sector'

    def lookups(self, request, model_admin):

        return [
            (sector.id, sector.name) for sector in Sector.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            sector = Sector.objects.get(pk=self.value())
            return queryset.filter(pca__sectors__icontains=sector.name)
        return queryset


class TPMPartnerFilter(admin.SimpleListFilter):

    title = 'Partner'
    parameter_name = 'partner'

    def lookups(self, request, model_admin):

        return [
            (partner.id, partner.name) for partner in PartnerOrganization.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            return queryset.filter(pca__partner__id=self.value())
        return queryset


class TPMVisitAdmin(ExportMixin, VersionAdmin):
    resource_class = TPMResource
    date_hierarchy = u'tentative_date'
    list_display = (
        u'status',
        u'cycle_number',
        u'pca',
        u'sectors',
        u'pca_location',
        u'assigned_by',
        u'tentative_date',
        u'completed_date'
    )
    list_filter = (
        u'pca',
        u'status',
        u'assigned_by',
        u'created_date',
        u'completed_date',
        u'cycle_number',
        SectorListFilter,
        TPMPartnerFilter,
    )
    readonly_fields = (
        u'pca',
        u'pca_location',
        u'assigned_by',
        u'unicef_manager',
        u'partner_manager',
    )

    def sectors(self, obj):
        return obj.pca.sector_names

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

    def has_module_permission(self, request):
        return request.user.is_superuser


admin.site.register(TPMVisit, TPMVisitAdmin)
