__author__ = 'jcranwellward'

from django.contrib import admin

from reversion.admin import VersionAdmin
from import_export.admin import ExportMixin

from reports.models import Sector
from partners.models import PartnerOrganization
from .models import TPMVisit
from .exports import TPMResource


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


class TPMLocationsAdmin(admin.ModelAdmin):
    list_display = (
        u'pca',
        u'sectors',
        u'location',
        u'view_location',
        u'tpm_visit',
    )
    list_filter = (
        u'pca',
        SectorListFilter,
        TPMPartnerFilter,
        u'location',
    )
    search_fields = (
        u'pca__number',
        u'location__name',
        u'location__gateway__name',
    )
    readonly_fields = (
        u'view_location',
        u'tpm_visit',
    )
    actions = ['create_tpm_visits']

    def sectors(self, obj):
        return obj.pca.sector_names

    # TODO PCALocation is undefined
    # def get_queryset(self, request):
    #     return PCALocation.objects.filter(
    #         pca__status=PCA.ACTIVE
    #     )

    def create_tpm_visits(self, request, queryset):
        for pca_location in queryset:
            TPMVisit.objects.create(
                pca=pca_location.pca,
                pca_location=pca_location,
                assigned_by=request.user
            )
            pca_location.tpm_visit = True
            pca_location.save()
        self.message_user(
            request,
            u'{} TPM visits created'.format(
                queryset.count()
            )
        )


admin.site.register(TPMVisit, TPMVisitAdmin)
