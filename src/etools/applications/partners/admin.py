from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.forms import SelectMultiple
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from import_export.admin import ExportMixin
from unicef_attachments.admin import AttachmentSingleInline
from unicef_attachments.models import Attachment
from unicef_snapshot.admin import ActivityInline, SnapshotModelAdmin

from etools.applications.partners.exports import PartnerExport
from etools.applications.partners.forms import (  # TODO intervention sector locations cleanup
    PartnersAdminForm,
    PartnerStaffMemberForm,
)
from etools.applications.partners.mixins import CountryUsersAdminMixin, HiddenPartnerMixin
from etools.applications.partners.models import (  # TODO intervention sector locations cleanup
    Agreement,
    AgreementAmendment,
    Assessment,
    CoreValuesAssessment,
    FileType,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    InterventionBudget,
    InterventionPlannedVisits,
    InterventionResultLink,
    PartnerOrganization,
    PartnerStaffMember,
    PlannedEngagement,
)


class InterventionAmendmentsAdmin(admin.ModelAdmin):
    model = InterventionAmendment
    readonly_fields = [
        'amendment_number',
    ]
    list_display = (
        'intervention',
        'types',
        'signed_date'
    )
    search_fields = ('intervention__number', )
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


class InterventionPlannedVisitsInline(admin.TabularInline):
    model = InterventionPlannedVisits
    fields = (
        'intervention',
        'year',
        'programmatic_q1',
        'programmatic_q2',
        'programmatic_q3',
        'programmatic_q4',
    )
    extra = 0


class AttachmentFileInline(AttachmentSingleInline):
    verbose_name_plural = _("Attachment")


class InterventionAttachmentAdmin(admin.ModelAdmin):
    model = InterventionAttachment
    list_display = (
        'attachment_file',
        'type',
    )
    list_filter = (
        'intervention',
    )
    fields = (
        'type',
        'attachment',
    )
    inlines = [
        AttachmentFileInline,
    ]

    def attachment_file(self, obj):
        content_type = ContentType.objects.get_for_model(obj)
        return Attachment.objects.get(
            object_id=obj.pk,
            content_type=content_type
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


class PRCReviewAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = _("Review Document by PRC")


class SignedPDAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = _("Signed PD Document")


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
        'attachments_link',
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
        'attachments_link',
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
                    'reference_number_year',
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
                 'population_focus',
                 'activation_letter',
                 ),
        }),
    )

    inlines = (
        InterventionAttachmentsInline,
        ActivityInline,
        PRCReviewAttachmentInline,
        SignedPDAttachmentInline,
        InterventionPlannedVisitsInline,
    )

    def created_date(self, obj):
        return obj.created_at.strftime('%d-%m-%Y')

    created_date.admin_order_field = '-created'

    def section_names(self, obj):
        return ' '.join([section.name for section in obj.sections.all()])

    section_names.short_description = "Sections"

    def has_module_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name='Country Office Administrator').exists()

    def attachments_link(self, obj):
        url = "{}?intervention__id__exact={}".format(
            reverse("admin:partners_interventionattachment_changelist"),
            obj.pk
        )
        return mark_safe("<a href='{}'>{}</a>".format(
            url,
            "Attachments"
        ))

    attachments_link.short_description = 'attachments'


class AssessmentReportInline(AttachmentSingleInline):
    verbose_name_plural = _("Report")


class AssessmentAdmin(admin.ModelAdmin):
    model = Assessment
    fields = (
        'partner',
        'type',
        'completed_date',
        'current',
        'report',
    )
    list_filter = (
        'partner',
        'type'
    )
    inlines = [
        AssessmentReportInline,
    ]


class PartnerStaffMemberAdmin(SnapshotModelAdmin):
    model = PartnerStaffMember
    form = PartnerStaffMemberForm

    # display_staff_member_name() is used only in list_display. It could be replaced by this simple lambda --
    #     lambda instance: str(instance)
    # However, creating a function allows me to put a title on the column in the admin by populating the function's
    # 'short_description' attribute.
    # https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    def display_staff_member_name(instance):
        return str(instance)
    display_staff_member_name.short_description = 'Partner Staff Member'

    list_display = (
        display_staff_member_name,
        'title',
        'email',
    )
    search_fields = (
        'first_name',
        'last_name',
        'email'
    )
    inlines = [
        ActivityInline,
    ]

    def has_module_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name='Country Office Administrator').exists()


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


class CoreValueAssessmentInline(admin.StackedInline):
    model = CoreValuesAssessment
    extra = 0


class PartnerAdmin(ExportMixin, admin.ModelAdmin):
    form = PartnersAdminForm
    resource_class = PartnerExport
    search_fields = (
        'name',
        'vendor_number',
    )
    list_filter = (
        'partner_type',
        'rating',
        HiddenPartnerFilter,
    )
    list_display = (
        'name',
        'vendor_number',
        'partner_type',
        'rating',
        'type_of_assessment',
        'email',
        'phone_number',
        'alternate_id',
        'alternate_name',
    )
    inlines = [
        CoreValueAssessmentInline,
    ]
    readonly_fields = (
        'vision_synced',
        'vendor_number',
        'rating',
        'type_of_assessment',
        'last_assessment_date',
        'core_values_assessment_date',
        'total_ct_cy',
        'total_ct_cp',
        'deleted_flag',
        'blocked',
        'name',
        'hact_values',
        'total_ct_cp',
        'total_ct_cy',
        'net_ct_cy',
        'reported_cy',
        'total_ct_ytd',
        'outstanding_dct_amount_6_to_9_months_usd',
        'outstanding_dct_amount_more_than_9_months_usd',
    )
    fieldsets = (
        (_('Partner Details'), {
            'fields':
                (('name', 'vision_synced',),
                 ('short_name', 'alternate_name',),
                 ('partner_type', 'cso_type',),
                 'shared_with',
                 'vendor_number',
                 'rating',
                 'type_of_assessment',
                 'last_assessment_date',
                 'address',
                 'city',
                 'postal_code',
                 'country',
                 'phone_number',
                 'email',
                 'core_values_assessment_date',
                 'manually_blocked',
                 'deleted_flag',
                 'blocked',
                 'hidden',
                 )
        }),
        (_('Hact'), {
            'fields': (
                'hact_values',
                'total_ct_cp',
                'total_ct_cy',
                'net_ct_cy',
                'reported_cy',
                'total_ct_ytd',
                'outstanding_dct_amount_6_to_9_months_usd',
                'outstanding_dct_amount_more_than_9_months_usd',
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
        return request.user.is_superuser or request.user.groups.filter(name='Country Office Administrator').exists()


class PlannedEngagementAdmin(admin.ModelAdmin):
    model = PlannedEngagement
    search_fields = (
        'partner__name',
    )
    fields = (
        'partner',
        'spot_check_follow_up',
        'spot_check_planned_q1',
        'spot_check_planned_q2',
        'spot_check_planned_q3',
        'spot_check_planned_q4',
        'scheduled_audit',
        'special_audit',
    )
    list_display = (
        'partner',
        'spot_check_follow_up',
        'spot_check_planned_q1',
        'spot_check_planned_q2',
        'spot_check_planned_q3',
        'spot_check_planned_q4',
        'scheduled_audit',
        'special_audit',
    )
    readonly_fields = [
        'partner',
    ]


class SignedAmendmentInline(AttachmentSingleInline):
    verbose_name_plural = _("Signed Amendment")


class AgreementAmendmentAdmin(admin.ModelAdmin):
    model = AgreementAmendment
    fields = (
        'agreement',
        'signed_amendment',
        'signed_date',
        'number',
        'types',
    )
    list_display = (
        'agreement',
        'number',
        'signed_amendment',
        'signed_date',
    )
    list_filter = (
        'agreement',
        'agreement__partner'
    )
    readonly_fields = [
        'number',
    ]
    inlines = [
        SignedAmendmentInline,
    ]

    def get_max_num(self, request, obj=None, **kwargs):
        """
        Overriding here to disable adding amendments to non-active partnerships
        """
        if obj and obj.agreement_type == Agreement.PCA:
            return self.max_num

        return 0


class AgreementAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = _('Attachment')


class AgreementAdmin(ExportMixin, HiddenPartnerMixin, CountryUsersAdminMixin, SnapshotModelAdmin):

    list_filter = (
        'partner',
        'agreement_type',
    )
    list_display = (
        'agreement_number',
        'partner',
        'agreement_type',
        'status',
        'signed_by_unicef_date',
    )
    fieldsets = (
        (_('Agreement Details'), {
            'fields':
                (
                    'partner',
                    'agreement_type',
                    'agreement_number',
                    'country_programme',
                    'status',
                    'attached_agreement',
                    ('start', 'end',),
                    'signed_by_partner_date',
                    'partner_manager',
                    'signed_by_unicef_date',
                    'signed_by',
                    'authorized_officers',
                )
        }),
    )
    filter_horizontal = (
        'authorized_officers',
    )
    inlines = [
        ActivityInline,
        AgreementAttachmentInline,
    ]

    def has_module_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name='Country Office Administrator').exists()


class FileTypeAdmin(admin.ModelAdmin):

    def has_module_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name='Country Office Administrator').exists()


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
admin.site.register(InterventionAttachment, InterventionAttachmentAdmin)

admin.site.register(FileType, FileTypeAdmin)
