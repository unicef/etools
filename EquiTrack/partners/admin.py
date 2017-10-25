from __future__ import absolute_import

from django.contrib import admin
from django.db import models
from django.forms import SelectMultiple
from django.utils.translation import ugettext_lazy as _
from generic_links.admin import GenericLinkStackedInline
from import_export.admin import ExportMixin

from EquiTrack.mixins import CountryUsersAdminMixin
from EquiTrack.stream_feed.actions import create_snapshot_activity_stream
from partners.exports import PartnerExport
from partners.forms import AgreementForm, PartnersAdminForm, PartnerStaffMemberForm, SectorLocationForm
from partners.mixins import HiddenPartnerMixin
from partners.models import (
    Agreement, AgreementAmendment, Assessment, FileType, FundingCommitment, Intervention, InterventionAmendment,
    InterventionAttachment, InterventionBudget, InterventionPlannedVisits, InterventionResultLink,
    InterventionSectorLocationLink, PartnerOrganization, PartnerStaffMember,)


class InterventionAmendmentsAdmin(admin.ModelAdmin):
    verbose_name = u'Amendment'
    model = InterventionAmendment
    readonly_fields = [
        'amendment_number',
    ]
    list_display = (
        'intervention',
        'types',
        'signed_date'
    )
    search_fields = ('intervention', )
    list_filter = (
        'intervention',
        'types'
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def get_max_num(self, request, obj=None, **kwargs):
        """
        Overriding here to disable adding amendments to non-active partnerships
        """
        if obj and obj.status == Intervention.ACTIVE:
            return self.max_num

        return 0


class LinksInlineAdmin(GenericLinkStackedInline):
    extra = 1


class InterventionBudgetAdmin(admin.ModelAdmin):
    model = InterventionBudget
    fields = (
        'intervention',
        'currency',
        'partner_contribution',
        'unicef_cash',
        'in_kind_amount',
        'partner_contribution_local',
        'unicef_cash_local',
        'in_kind_amount_local',
        'total',
    )
    list_display = (
        'intervention',
        'total'
    )
    list_filter = (
        'intervention',
    )
    search_fields = (
        'intervention__number',
    )
    readonly_fields = ('total', )
    extra = 0


class InterventionPlannedVisitsAdmin(admin.ModelAdmin):
    model = InterventionPlannedVisits
    fields = (
        'intervention',
        'year',
        'programmatic',
        'spot_checks',
        'audit'
    )
    search_fields = (
        'intervention__number',
    )
    list_display = (
        'intervention',
        'year',
        'programmatic',
        'spot_checks',
        'audit'
    )


class InterventionAttachmentsInline(admin.TabularInline):
    model = InterventionAttachment
    fields = (
        'type',
        'attachment',
    )
    extra = 0


class InterventionResultsLinkAdmin(admin.ModelAdmin):

    # form = ResultLinkForm
    model = InterventionResultLink
    fields = (
        'intervention',
        'cp_output',
        'ram_indicators'
    )
    list_display = (
        'intervention',
        'cp_output',
    )
    list_filter = (
        'intervention',
        'cp_output',
    )
    search_fields = (
        'intervention__name',
    )
    formfield_overrides = {
        models.ManyToManyField: {'widget': SelectMultiple(attrs={'size': '5', 'style': 'width:100%'})},
    }


class InterventionSectorLocationAdmin(admin.ModelAdmin):
    form = SectorLocationForm
    model = InterventionSectorLocationLink
    fields = (
        'intervention',
        'sector',
        'locations'
    )
    list_display = (
        'intervention',
        'sector'
    )
    search_fields = (
        'intervention__name',
    )
    list_filter = (
        'sector',
    )


class InterventionAdmin(CountryUsersAdminMixin, HiddenPartnerMixin, admin.ModelAdmin):

    date_hierarchy = 'start'
    list_display = (
        'number',
        'document_type',
        'status',
        'created',
        'signed_by_unicef_date',
        'start',
        'end',
        'sector_names',
        'title',
        'total_unicef_cash',
        'total_budget',
    )
    list_filter = (
        'number',
        'agreement__partner',
        'document_type',
        'status',
    )
    search_fields = (
        'number',
        'title',
    )
    readonly_fields = (
        'total_budget',
    )
    filter_horizontal = (
        'unicef_focal_points',
        'partner_focal_points'
    )
    fieldsets = (
        (_('Intervention Details'), {
            'fields':
                (
                    'agreement',
                    'document_type',
                    'number',
                    'title',
                    'status',
                    'country_programme',
                    'submission_date',
                    'metadata',
                )
        }),
        (_('Dates and Signatures'), {
            'fields':
                (('submission_date_prc',),
                 'review_date_prc',
                 'prc_review_document',
                 'signed_pd_document',
                 ('partner_authorized_officer_signatory', 'signed_by_partner_date',),
                 ('unicef_signatory', 'signed_by_unicef_date',),
                 'partner_focal_points',
                 'unicef_focal_points',
                 # ('days_from_submission_to_signed', 'days_from_review_to_signed',),
                 ('start', 'end'),
                 'population_focus'),
        }),
    )

    inlines = (
        # InterventionAmendmentsInlineAdmin,
        # BudgetInlineAdmin,
        # PlannedVisitsInline,
        # ResultsLinkInline,
        # SectorLocationInline,
        InterventionAttachmentsInline,
    )

    def created_date(self, obj):
        return obj.created_at.strftime('%d-%m-%Y')

    created_date.admin_order_field = '-created'

    def save_model(self, request, obj, form, change):
        created = False if change else True
        create_snapshot_activity_stream(request.user, obj, created=created)

        super(InterventionAdmin, self).save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return request.user.is_superuser


class AssessmentAdmin(admin.ModelAdmin):
    model = Assessment
    fields = (
        u'partner',
        u'type',
        u'completed_date',
        u'current',
        u'report',
    )
    list_filter = (
        u'partner',
        u'type'
    )
    verbose_name = u'Assessment'
    verbose_name_plural = u'Assessments'


class PartnerStaffMemberAdmin(admin.ModelAdmin):
    model = PartnerStaffMember
    form = PartnerStaffMemberForm

    # display_staff_member_name() is used only in list_display. It could be replaced by this simple lambda --
    #     lambda instance: unicode(instance)
    # However, creating a function allows me to put a title on the column in the admin by populating the function's
    # 'short_description' attribute.
    # https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    def display_staff_member_name(instance):
        return unicode(instance)
    display_staff_member_name.short_description = 'Partner Staff Member'

    list_display = (
        display_staff_member_name,
        'title',
        'email',
    )
    search_fields = (
        u'first_name',
        u'last_name',
        u'email'
    )

    def save_model(self, request, obj, form, change):
        created = False if change else True
        create_snapshot_activity_stream(request.user, obj, created=created)

        super(PartnerStaffMemberAdmin, self).save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return request.user.is_superuser


class HiddenPartnerFilter(admin.SimpleListFilter):

    title = 'Show Hidden'
    parameter_name = 'hidden'

    def lookups(self, request, model_admin):

        return [
            (True, 'Yes'),
            (False, 'No')
        ]

    def queryset(self, request, queryset):

        value = self.value()
        if value == 'True':
            return queryset.filter(hidden=True)
        return queryset.filter(hidden=False)


class PartnerAdmin(ExportMixin, admin.ModelAdmin):
    form = PartnersAdminForm
    resource_class = PartnerExport
    search_fields = (
        u'name',
        u'vendor_number',
    )
    list_filter = (
        u'partner_type',
        HiddenPartnerFilter,
    )
    list_display = (
        u'name',
        u'vendor_number',
        u'partner_type',
        u'email',
        u'phone_number',
        u'alternate_id',
        u'alternate_name',
    )
    readonly_fields = (
        u'vision_synced',
        u'vendor_number',
        u'rating',
        u'type_of_assessment',
        u'last_assessment_date',
        u'core_values_assessment_date',
        u'deleted_flag',
        u'blocked'
    )
    fieldsets = (
        (_('Partner Details'), {
            'fields':
                ((u'name', u'vision_synced',),
                 (u'short_name', u'alternate_name',),
                 (u'partner_type', u'cso_type',),
                 u'shared_with',
                 u'vendor_number',
                 u'rating',
                 u'type_of_assessment',
                 u'last_assessment_date',
                 u'address',
                 u'city',
                 u'postal_code',
                 u'country',
                 u'phone_number',
                 u'email',
                 u'core_values_assessment_date',
                 u'core_values_assessment',
                 u'hidden',
                 u'deleted_flag',
                 u'blocked',
                 )
        }),
    )
    actions = (
        'hide_partners',
        'show_partners'
    )

    def hide_partners(self, request, queryset):

        partners = 0
        for partner in queryset:
            partner.hidden = True
            partner.save()
            partners += 1
        self.message_user(request, '{} partners were hidden'.format(partners))

    def show_partners(self, request, queryset):

        partners = 0
        for partner in queryset:
            partner.hidden = False
            partner.save()
            partners += 1
        self.message_user(request, '{} partners were shown'.format(partners))

    def has_module_permission(self, request):
        return request.user.is_superuser


class AgreementAmendmentAdmin(admin.ModelAdmin):
    verbose_name = u'Amendment'
    model = AgreementAmendment
    fields = (
        'signed_amendment',
        'signed_date',
        'number',
        'types',
    )
    list_display = (
        u'agreement',
        u'number',
        u'signed_amendment',
        u'signed_date',
    )
    list_filter = (
        u'agreement',
        u'agreement__partner'
    )
    readonly_fields = [
        'number',
    ]

    def get_max_num(self, request, obj=None, **kwargs):
        """
        Overriding here to disable adding amendments to non-active partnerships
        """
        if obj and obj.agreement_type == Agreement.PCA:
            return self.max_num

        return 0


class AgreementAdmin(ExportMixin, HiddenPartnerMixin, CountryUsersAdminMixin, admin.ModelAdmin):
    form = AgreementForm
    list_filter = (
        u'partner',
        u'agreement_type',
    )
    list_display = (
        u'agreement_number',
        u'partner',
        u'agreement_type',
        u'status',
        u'signed_by_unicef_date',
    )
    fieldsets = (
        (_('Agreement Details'), {
            'fields':
                (
                    u'partner',
                    u'agreement_type',
                    u'agreement_number',
                    u'country_programme',
                    u'status',
                    u'attached_agreement',
                    (u'start', u'end',),
                    u'signed_by_partner_date',
                    u'partner_manager',
                    u'signed_by_unicef_date',
                    u'signed_by',
                    u'authorized_officers',
                )
        }),
    )
    filter_horizontal = (
        u'authorized_officers',
    )

    def save_model(self, request, obj, form, change):
        created = False if change else True
        create_snapshot_activity_stream(request.user, obj, created=created)

        super(AgreementAdmin, self).save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return request.user.is_superuser


class FundingCommitmentAdmin(admin.ModelAdmin):
    search_fields = (
        u'fr_number',
        u'grant__name',
    )
    list_filter = (
        u'grant',
    )
    list_display = (
        u'fc_ref',
        u'grant',
        u'fr_number',
        u'fr_item_amount_usd',
        u'agreement_amount',
        u'commitment_amount',
        u'expenditure_amount',
    )
    readonly_fields = list_display + (
        u'wbs',
        u'fc_type',
        u'start',
        u'end',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        created = False if change else True
        create_snapshot_activity_stream(request.user, obj, created=created)

        super(FundingCommitmentAdmin, self).save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return request.user.is_superuser


class FileTypeAdmin(admin.ModelAdmin):

    def has_module_permission(self, request):
        return request.user.is_superuser


admin.site.register(PartnerOrganization, PartnerAdmin)
admin.site.register(Assessment, AssessmentAdmin)
admin.site.register(PartnerStaffMember, PartnerStaffMemberAdmin)


admin.site.register(Agreement, AgreementAdmin)
admin.site.register(AgreementAmendment, AgreementAmendmentAdmin)


admin.site.register(Intervention, InterventionAdmin)
admin.site.register(InterventionAmendment, InterventionAmendmentsAdmin)
admin.site.register(InterventionResultLink, InterventionResultsLinkAdmin)
admin.site.register(InterventionBudget, InterventionBudgetAdmin)
admin.site.register(InterventionPlannedVisits, InterventionPlannedVisitsAdmin)
admin.site.register(InterventionSectorLocationLink, InterventionSectorLocationAdmin)


admin.site.register(FileType, FileTypeAdmin)
admin.site.register(FundingCommitment, FundingCommitmentAdmin)
