from django.contrib import admin, messages
from django.contrib.admin.utils import quote
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.forms import SelectMultiple
from django.http.response import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from admin_extra_urls.decorators import button
from admin_extra_urls.mixins import ExtraUrlMixin
from import_export.admin import ExportMixin
from unicef_attachments.admin import AttachmentSingleInline
from unicef_attachments.models import Attachment
from unicef_snapshot.admin import ActivityInline, SnapshotModelAdmin

from etools.applications.partners.exports import PartnerExport
from etools.applications.partners.forms import (  # TODO intervention sector locations cleanup
    InterventionAttachmentForm,
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
    InterventionManagementBudget,
    InterventionManagementBudgetItem,
    InterventionPlannedVisits,
    InterventionResultLink,
    InterventionReview,
    InterventionSupplyItem,
    PartnerOrganization,
    PartnerStaffMember,
    PlannedEngagement,
)
from etools.applications.partners.tasks import sync_partner
from etools.libraries.djangolib.admin import RestrictedEditAdmin, RestrictedEditAdminMixin


class InterventionReviewInlineAdmin(RestrictedEditAdminMixin, admin.TabularInline):
    model = InterventionReview
    extra = 0

    raw_id_fields = [
        "prc_officers",
        "submitted_by",
        "overall_approver"
    ]


class AttachmentSingleInline(RestrictedEditAdminMixin, AttachmentSingleInline):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(code=self.code)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.code = self.code
        return formset


class AttachmentInlineAdminMixin:
    def save_formset(self, request, form, formset, change):
        instances = formset.save()
        for instance in instances:
            instance.code = formset.code
            instance.save()


class InterventionAmendmentSignedInline(AttachmentSingleInline):
    verbose_name_plural = _("Signed Attachment")
    code = 'partners_intervention_amendment_signed'


class InterventionAmendmentPRCReviewInline(AttachmentSingleInline):
    verbose_name_plural = _("PRC Reviewed Attachment")
    code = 'partners_intervention_amendment_internal_prc_review'


class InterventionAmendmentsAdmin(AttachmentInlineAdminMixin, CountryUsersAdminMixin, RestrictedEditAdmin):
    staff_only = False
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
    inlines = [
        InterventionAmendmentSignedInline,
        InterventionAmendmentPRCReviewInline,
    ]

    def has_delete_permission(self, request, obj=None):
        return False

    def get_max_num(self, request, obj=None, **kwargs):
        """
        Overriding here to disable adding amendments to non-active partnerships
        """
        if obj and obj.status == Intervention.ACTIVE:
            return self.max_num

        return 0


class InterventionBudgetAdmin(RestrictedEditAdmin):
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


class InterventionPlannedVisitsAdmin(RestrictedEditAdmin):
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


class InterventionPlannedVisitsInline(RestrictedEditAdminMixin, admin.TabularInline):
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
    code = 'partners_intervention_attachment'


class InterventionAttachmentAdmin(AttachmentInlineAdminMixin, RestrictedEditAdmin):
    model = InterventionAttachment
    list_display = (
        'intervention',
        'attachment',
        'type',
    )
    list_filter = (
        'intervention',
    )
    fields = (
        'intervention',
        'type',
    )
    inlines = [
        AttachmentFileInline,
    ]


class InterventionAttachmentsInline(RestrictedEditAdminMixin, admin.TabularInline):
    model = InterventionAttachment
    form = InterventionAttachmentForm
    fields = (
        'type',
        'attachment',
    )
    extra = 0
    code = 'partners_intervention_attachment'

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.code = self.code
        return formset


class InterventionResultsLinkAdmin(RestrictedEditAdmin):

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
        'intervention__title',
    )
    formfield_overrides = {
        models.ManyToManyField: {'widget': SelectMultiple(attrs={'size': '5', 'style': 'width:100%'})},
    }


class PRCReviewAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = _("Review Document by PRC")
    code = 'partners_intervention_prc_review'


class SignedPDAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = _("Signed PD Document")
    code = 'partners_intervention_signed_pd'


class InterventionAdmin(
        AttachmentInlineAdminMixin,
        CountryUsersAdminMixin,
        HiddenPartnerMixin,
        RestrictedEditAdminMixin,
        SnapshotModelAdmin
):
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
    raw_id_fields = [
        'agreement',
        'flat_locations',
        'partner_authorized_officer_signatory',
        'old_partner_authorized_officer_signatory',  # TODO REALMS clean up
        'unicef_signatory',
        'budget_owner',
        'unicef_focal_points',
        'partner_focal_points',
        'old_partner_focal_points',  # TODO REALMS clean up
    ]
    list_filter = (
        'document_type',
        'status',
    )
    search_fields = (
        'number',
        'title',
        'agreement__partner__name'
    )
    readonly_fields = (
        'total_budget',
        'attachments_link',
        'prc_review_document',
        'signed_pd_document',
    )
    filter_horizontal = (
        'sections',
        'unicef_focal_points',
        'old_partner_focal_points',  # TODO REALMS clean up
        'partner_focal_points',
        'flat_locations'
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
                    'country_programmes',
                    'submission_date',
                    'sections',
                    'flat_locations',
                    'metadata',
                )
        }),
        (_('Dates and Signatures'), {
            'fields':
                (('submission_date_prc',),
                 'review_date_prc',
                 'prc_review_document',
                 'signed_pd_document',
                 ('old_partner_authorized_officer_signatory', 'signed_by_partner_date',),  # TODO REALMS clean up
                 'partner_authorized_officer_signatory',
                 ('unicef_signatory', 'signed_by_unicef_date',),
                 'old_partner_focal_points',  # TODO REALMS clean up
                 'partner_focal_points',
                 'unicef_focal_points',
                 ('start', 'end'),
                 'population_focus',
                 'activation_letter',
                 'activation_protocol'
                 ),
        }),
        (_('ePD'), {
            'fields': (
                'unicef_court',
                'date_sent_to_partner',
                ('unicef_accepted', 'partner_accepted'),
                'cfei_number',
                'context',
                'implementation_strategy',
                ('gender_rating', 'gender_narrative'),
                ('equity_rating', 'equity_narrative'),
                ('sustainability_rating', 'sustainability_narrative'),
                'budget_owner',
                'hq_support_cost',
                'cash_transfer_modalities',
                'unicef_review_type',
                'capacity_development',
                'other_info',
                'other_partners_involved',
                'technical_guidance',
            )
        }),
    )

    inlines = (
        InterventionAttachmentsInline,
        ActivityInline,
        PRCReviewAttachmentInline,
        SignedPDAttachmentInline,
        InterventionPlannedVisitsInline,
        InterventionReviewInlineAdmin,
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

    def save_formset(self, request, form, formset, change):
        instances = formset.save()
        for instance in instances:
            if isinstance(instance, InterventionAttachment):
                # update attachment file data
                content_type = ContentType.objects.get_for_model(instance)
                Attachment.objects.update_or_create(
                    object_id=instance.pk,
                    content_type=content_type,
                    defaults={
                        "code": formset.code,
                        "file": instance.attachment,
                        "uploaded_by": request.user,
                    }
                )


class AssessmentReportInline(AttachmentSingleInline):
    verbose_name_plural = _("Report")
    code = 'partners_assessment_report'


class AssessmentAdmin(AttachmentInlineAdminMixin, RestrictedEditAdmin):
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


class PartnerStaffMemberAdmin(RestrictedEditAdminMixin, SnapshotModelAdmin):
    model = PartnerStaffMember
    form = PartnerStaffMemberForm
    raw_id_fields = ("partner", "user",)

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
        'user',
    )
    search_fields = (
        'first_name',
        'last_name',
        'email',
        'user__first_name',
        'user__last_name',
        'partner__organization__name'
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
        if not value:
            return queryset
        if value == 'True':
            return queryset.filter(hidden=True)
        return queryset.filter(hidden=False)


class CoreValueAssessmentInline(RestrictedEditAdminMixin, admin.StackedInline):
    model = CoreValuesAssessment
    extra = 0


class PartnerAdmin(ExtraUrlMixin, ExportMixin, RestrictedEditAdmin):
    resource_class = PartnerExport
    search_fields = (
        'alternate_name',
        'organization__name',
        'organization__vendor_number',
        'organization__short_name'
    )
    autocomplete_fields = ('lead_office', 'lead_section')
    list_filter = (
        'organization__organization_type',
        'rating',
        HiddenPartnerFilter,
    )
    list_display = (
        'organization',
        'rating',
        'highest_risk_rating_name',
        'highest_risk_rating_type',
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
        'organization',
        'rating',
        'type_of_assessment',
        'last_assessment_date',
        'core_values_assessment_date',
        'total_ct_cy',
        'total_ct_cp',
        'deleted_flag',
        'blocked',
        'hact_values',
        'total_ct_cp',
        'total_ct_cy',
        'net_ct_cy',
        'reported_cy',
        'total_ct_ytd',
        'outstanding_dct_amount_6_to_9_months_usd',
        'outstanding_dct_amount_more_than_9_months_usd',
        'psea_assessment_date',
        'sea_risk_rating_name',
        'highest_risk_rating_name',
        'highest_risk_rating_type',
    )
    fieldsets = (
        (_('Partner Details'), {
            'fields':
                (('organization', 'vision_synced',),
                 'lead_office',
                 'lead_section',
                 'shared_with',
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
                 'psea_assessment_date',
                 'sea_risk_rating_name',
                 'highest_risk_rating_name',
                 'highest_risk_rating_type',
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

    @button()
    def sync_partner(self, request, pk):
        sync_partner(PartnerOrganization.objects.get(id=pk).vendor_number, request.user.profile.country)
        return HttpResponseRedirect(reverse('admin:partners_partnerorganization_change', args=[pk]))

    @button()
    def update_hact(self, request, pk):
        obj = self.get_object(request, pk)
        obj.update_planned_visits_to_hact()
        obj.update_programmatic_visits()
        obj.update_spot_checks()
        obj.update_audits_completed()
        obj.update_hact_support()
        obj.update_min_requirements()


class PlannedEngagementAdmin(RestrictedEditAdmin):
    model = PlannedEngagement
    search_fields = (
        'partner__organization__name',
        'partner__organization__short_name',
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

    def has_add_permission(self, request):
        return False


class SignedAmendmentInline(AttachmentSingleInline):
    verbose_name_plural = _("Signed Amendment")
    code = 'partners_agreement_amendment'


class AgreementAmendmentAdmin(AttachmentInlineAdminMixin, RestrictedEditAdmin):
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
    code = 'partners_agreement'


class AgreementAdmin(
        AttachmentInlineAdminMixin,
        ExportMixin,
        HiddenPartnerMixin,
        CountryUsersAdminMixin,
        RestrictedEditAdminMixin,
        SnapshotModelAdmin,
):
    staff_only = False

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
    search_fields = (
        'agreement_number',
        'partner__organization__name',
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
                    'old_partner_manager',  # TODO REALMS clean up
                    'partner_manager',
                    'signed_by_unicef_date',
                    'signed_by',
                    'authorized_officers',
                    'old_authorized_officers',  # TODO REALMS clean up
                )
        }),
    )
    filter_horizontal = (
        'authorized_officers',
        'old_authorized_officers',  # TODO REALMS clean up
    )
    inlines = [
        ActivityInline,
        AgreementAttachmentInline,
    ]

    def has_module_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name='Country Office Administrator').exists()

    def get_deleted_objects(self, objs, request):
        deleted_objects, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)
        if 'interventions' in model_count and model_count['interventions'] != 0:
            if 'action' in request.POST and request.POST['action'] == 'delete_selected':
                messages.error(
                    request,
                    _('Please delete all interventions associated with the selected Agreements '
                      'before deleting them.')
                )
            else:
                messages.error(
                    request,
                    _('Please delete all interventions associated with this Agreement '
                      'before deleting the agreement.')
                )
            protected.extend(self.get_interventions_admin_urls(objs))

        return deleted_objects, model_count, perms_needed, protected

    def get_interventions_admin_urls(self, objs):
        urls = []

        agreement_ids = [agreement.id for agreement in objs] if isinstance(objs, list) else \
            objs.values_list('id', flat=True)
        for intervention_obj in Intervention.objects.filter(agreement_id__in=agreement_ids):
            intervention_url = reverse(
                'admin:%s_%s_change' %
                (intervention_obj._meta.app_label, intervention_obj._meta.model_name),
                args=(quote(intervention_obj.pk),),
                current_app=self.admin_site.name
            )
            formatted_url = format_html(
                '{} : <a href="{}">{}</a>',
                intervention_obj._meta.model.__name__,
                intervention_url,
                intervention_obj
            )
            urls.append(formatted_url)
        return urls


class FileTypeAdmin(RestrictedEditAdmin):

    def has_module_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name='Country Office Administrator').exists()


class InterventionManagementBudgetItemAdmin(RestrictedEditAdminMixin, admin.StackedInline):
    model = InterventionManagementBudgetItem


class InterventionManagementBudgetAdmin(RestrictedEditAdmin):
    list_display = ('intervention',)
    list_select_related = ('intervention',)
    inlines = (InterventionManagementBudgetItemAdmin,)


class InterventionSupplyItemAdmin(RestrictedEditAdmin):
    list_display = ('intervention', 'title', 'unit_number', 'unit_price', 'provided_by')
    list_select_related = ('intervention',)
    list_filter = ('provided_by',)
    search_fields = ('title',)


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
admin.site.register(InterventionManagementBudget, InterventionManagementBudgetAdmin)
admin.site.register(InterventionSupplyItem, InterventionSupplyItemAdmin)

admin.site.register(FileType, FileTypeAdmin)
