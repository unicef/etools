
from django.contrib import admin
from django.db import models
from django.forms import SelectMultiple
from django.utils import six
from django.utils.translation import ugettext_lazy as _

from import_export.admin import ExportMixin

from etools.applications.EquiTrack.admin import ActivityInline, SnapshotModelAdmin
from etools.applications.partners.exports import PartnerExport
from etools.applications.partners.forms import PartnersAdminForm  # TODO intervention sector locations cleanup
from etools.applications.partners.forms import PartnerStaffMemberForm, SectorLocationForm
from etools.applications.partners.mixins import CountryUsersAdminMixin, HiddenPartnerMixin
from etools.applications.partners.models import Agreement  # TODO intervention sector locations cleanup
from etools.applications.partners.models import (AgreementAmendment, Assessment, FileType, FundingCommitment,
                                                 Intervention, InterventionAmendment, InterventionAttachment,
                                                 InterventionBudget, InterventionPlannedVisits, InterventionResultLink,
                                                 InterventionSectorLocationLink, PartnerOrganization,
                                                 PartnerStaffMember, PlannedEngagement,)


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
        'programmatic_q1',
        'programmatic_q2',
        'programmatic_q3',
        'programmatic_q4',
    )
    search_fields = (
        'intervention__number',
    )
    list_display = (
        'intervention',
        'year',
        'programmatic_q1',
        'programmatic_q2',
        'programmatic_q3',
        'programmatic_q4',
    )


class InterventionAttachmentsInline(admin.TabularInline):
    model = InterventionAttachment
    fields = (
        'type',
        'attachment',
    )
    extra = 0


class InterventionResultsLinkAdmin(admin.ModelAdmin):

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


# TODO intervention sector locations cleanup
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


class InterventionAdmin(CountryUsersAdminMixin, HiddenPartnerMixin, SnapshotModelAdmin):
    model = Intervention

    date_hierarchy = 'start'
    list_display = (
        'number',
        'document_type',
        'status',
        'created',
        'signed_by_unicef_date',
        'start',
        'end',
        'section_names',
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
        'sections',
        'unicef_focal_points',
        'partner_focal_points'
    )
    fieldsets = (
        (_('Intervention Details'), {
            'fields':
                (
                    'agreement',
                    'in_amendment',
                    'document_type',
                    'number',
                    'title',
                    'status',
                    'country_programme',
                    'submission_date',
                    'sections',
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
                 ('start', 'end'),
                 'population_focus'),
        }),
    )

    inlines = (
        InterventionAttachmentsInline,
        ActivityInline,
    )

    def created_date(self, obj):
        return obj.created_at.strftime('%d-%m-%Y')

    created_date.admin_order_field = '-created'

    def section_names(self, obj):
        return ' '.join([section.name for section in obj.sections.all()])

    section_names.short_description = "Sections"

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


class PartnerStaffMemberAdmin(SnapshotModelAdmin):
    model = PartnerStaffMember
    form = PartnerStaffMemberForm

    # display_staff_member_name() is used only in list_display. It could be replaced by this simple lambda --
    #     lambda instance: six.text_type(instance)
    # However, creating a function allows me to put a title on the column in the admin by populating the function's
    # 'short_description' attribute.
    # https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    def display_staff_member_name(instance):
        return six.text_type(instance)
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
    inlines = [
        ActivityInline,
    ]

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
        u'rating',
        HiddenPartnerFilter,
    )
    list_display = (
        u'name',
        u'vendor_number',
        u'partner_type',
        u'rating',
        u'type_of_assessment',
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
        u'total_ct_cy',
        u'total_ct_cp',
        u'deleted_flag',
        u'blocked',
        u'name',
        u'hact_values',
        u'total_ct_cp',
        u'total_ct_cy',
        u'net_ct_cy',
        u'reported_cy',
        u'total_ct_ytd',
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
        (_('Hact'), {
            'fields': (
                u'hact_values',
                u'total_ct_cp',
                u'total_ct_cy',
                u'net_ct_cy',
                u'reported_cy',
                u'total_ct_ytd',
            )
        })
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


class PlannedEngagementAdmin(admin.ModelAdmin):
    model = PlannedEngagement
    search_fields = (
        u'partner__name',
    )
    fields = (
        u'partner',
        u'spot_check_mr',
        u'spot_check_follow_up_q1',
        u'spot_check_follow_up_q2',
        u'spot_check_follow_up_q3',
        u'spot_check_follow_up_q4',
        u'scheduled_audit',
        u'special_audit',
    )
    list_display = (
        u'partner',
        u'spot_check_mr',
        u'spot_check_follow_up_q1',
        u'spot_check_follow_up_q2',
        u'spot_check_follow_up_q3',
        u'spot_check_follow_up_q4',
        u'scheduled_audit',
        u'special_audit',
    )
    readonly_fields = [
        u'partner',
    ]


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


class AgreementAdmin(ExportMixin, HiddenPartnerMixin, CountryUsersAdminMixin, SnapshotModelAdmin):

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
    inlines = [
        ActivityInline,
    ]

    def has_module_permission(self, request):
        return request.user.is_superuser


class FundingCommitmentAdmin(SnapshotModelAdmin):
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
    inlines = [
        ActivityInline,
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return request.user.is_superuser


class FileTypeAdmin(admin.ModelAdmin):

    def has_module_permission(self, request):
        return request.user.is_superuser


admin.site.register(PartnerOrganization, PartnerAdmin)
admin.site.register(Assessment, AssessmentAdmin)
admin.site.register(PartnerStaffMember, PartnerStaffMemberAdmin)
admin.site.register(PlannedEngagement, PlannedEngagementAdmin)

admin.site.register(Agreement, AgreementAdmin)
admin.site.register(AgreementAmendment, AgreementAmendmentAdmin)


admin.site.register(Intervention, InterventionAdmin)
admin.site.register(InterventionAmendment, InterventionAmendmentsAdmin)
admin.site.register(InterventionResultLink, InterventionResultsLinkAdmin)
admin.site.register(InterventionBudget, InterventionBudgetAdmin)
admin.site.register(InterventionPlannedVisits, InterventionPlannedVisitsAdmin)
# TODO intervention sector locations cleanup
admin.site.register(InterventionSectorLocationLink, InterventionSectorLocationAdmin)


admin.site.register(FileType, FileTypeAdmin)
admin.site.register(FundingCommitment, FundingCommitmentAdmin)
