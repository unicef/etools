from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.forms import SelectMultiple
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from admin_extra_urls.decorators import button
from admin_extra_urls.mixins import ExtraUrlMixin
from django_tenants.postgresql_backend.base import FakeTenant
from unicef_attachments.admin import AttachmentSingleInline
from unicef_attachments.models import Attachment
from unicef_snapshot.admin import ActivityInline, SnapshotModelAdmin

from etools.applications.governments.models import GovIntervention, GovernmentResultLink, GovernmentAmendment, \
    GovernmentBudget, GovernmentPlannedVisits, GovernmentAttachment, GovernmentSupplyItem, GovernmentReview
from etools.applications.partners.mixins import CountryUsersAdminMixin, HiddenPartnerMixin
from etools.applications.partners.models import Intervention
from etools.applications.partners.synchronizers import PDVisionUploader
from etools.applications.partners.tasks import send_pd_to_vision, sync_partner
from etools.libraries.djangolib.admin import RestrictedEditAdmin, RestrictedEditAdminMixin


class GovernmentReviewInlineAdmin(RestrictedEditAdminMixin, admin.TabularInline):
    model = GovernmentReview
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


class GovernmentAmendmentSignedInline(AttachmentSingleInline):
    verbose_name_plural = _("Signed Attachment")
    code = 'government_intervention_amendment_signed'


class GovernmentAmendmentPRCReviewInline(AttachmentSingleInline):
    verbose_name_plural = _("PRC Reviewed Attachment")
    code = 'government_intervention_amendment_internal_prc_review'


class GovernmentAmendmentsAdmin(AttachmentInlineAdminMixin, CountryUsersAdminMixin, RestrictedEditAdmin):
    staff_only = False
    model = GovernmentAmendment
    readonly_fields = [
        'amendment_number',
    ]
    raw_id_fields = [
        'intervention',
        'amended_intervention',
        'unicef_signatory',
        'partner_authorized_officer_signatory',
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
        GovernmentAmendmentSignedInline,
        GovernmentAmendmentPRCReviewInline,
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


class GovernmentBudgetAdmin(RestrictedEditAdmin):
    model = GovernmentBudget
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


class GovernmentPlannedVisitsAdmin(RestrictedEditAdmin):
    model = GovernmentPlannedVisits
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


class GovernmentPlannedVisitsInline(RestrictedEditAdminMixin, admin.TabularInline):
    model = GovernmentPlannedVisits
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
    code = 'government_intervention_attachment'


class GovernmentAttachmentAdmin(AttachmentInlineAdminMixin, RestrictedEditAdmin):
    model = GovernmentAttachment
    list_display = (
        'intervention',
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


class GovernmentAttachmentsInline(RestrictedEditAdminMixin, admin.TabularInline):
    model = GovernmentAttachment
    fields = ('type',)
    extra = 0
    code = 'government_intervention_attachment'

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.code = self.code
        return formset


class GovernmentResultsLinkAdmin(RestrictedEditAdmin):

    model = GovernmentResultLink
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
    code = 'government_intervention_prc_review'


class SignedPDAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = _("Signed PD Document")
    code = 'government_intervention_signed_pd'


class GovInterventionAdmin(
        ExtraUrlMixin,
        AttachmentInlineAdminMixin,
        CountryUsersAdminMixin,
        HiddenPartnerMixin,
        RestrictedEditAdminMixin,
        SnapshotModelAdmin
):
    model = GovIntervention

    staff_only = False

    date_hierarchy = 'start'
    list_display = (
        'number',
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
        'partner_organization',
        'flat_locations',
        'partner_authorized_officer_signatory',
        'unicef_signatory',
        'budget_owner',
        'unicef_focal_points',
        'partner_focal_points',
    ]
    list_filter = (
        'status',
    )
    search_fields = (
        'number',
        'title',
        'partner__organization__name'
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
        'partner_focal_points',
        'flat_locations'
    )
    country_office_admin_editable = ('unicef_court', )
    fieldsets = (
        (_('Intervention Details'), {
            'fields':
                (
                    'agreement',
                    'partner_organization',
                    'in_amendment',
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
                 ('partner_authorized_officer_signatory', 'signed_by_partner_date',),
                 ('unicef_signatory', 'signed_by_unicef_date',),
                 'partner_focal_points',
                 'unicef_focal_points',
                 ('start', 'end'),
                 'population_focus',
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
                (
                    'has_data_processing_agreement',
                    'has_activities_involving_children',
                    'has_special_conditions_for_construction',
                ),
            )
        }),
    )

    inlines = (
        GovernmentAttachmentsInline,
        ActivityInline,
        PRCReviewAttachmentInline,
        SignedPDAttachmentInline,
        GovernmentPlannedVisitsInline,
        GovernmentReviewInlineAdmin,
    )

    @button(label='Send to Vision')
    def send_to_vision(self, request, pk):
        if not PDVisionUploader(Intervention.objects.get(pk=pk)).is_valid():
            messages.error(request, _('PD is not ready for Vision synchronization.'))
            return

        send_pd_to_vision.delay(connection.tenant.name, pk)
        messages.success(request, _('PD was sent to Vision.'))

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
            reverse("admin:government_interventionattachment_changelist"),
            obj.pk
        )
        return mark_safe("<a href='{}'>{}</a>".format(
            url,
            "Attachments"
        ))

    attachments_link.short_description = 'attachments'

    def has_change_permission(self, request, obj=None):
        if isinstance(connection.tenant, FakeTenant):
            return False
        return super().has_change_permission(request, obj=None) or request.user.groups.filter(name='Country Office Administrator').exists()

    def changeform_view(self, request, *args, **kwargs):
        self.readonly_fields = list(self.readonly_fields)

        if request.user.groups.filter(name='Country Office Administrator').exists() and \
                request.user.email not in settings.ADMIN_EDIT_EMAILS:
            form_fields = [field for field in self.get_fields(request)
                           if field not in self.country_office_admin_editable]
            self.readonly_fields.extend(form_fields)

        return super().changeform_view(request, *args, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        _new_hq_cost_label = _('Capacity Strengthening Costs')
        if 'hq_support_cost' in form.base_fields:  # when user has change permissions
            form.base_fields['hq_support_cost'].label = _new_hq_cost_label
        else:  # in view only more
            form._meta.labels = {'hq_support_cost': _new_hq_cost_label}
        return form

    def save_formset(self, request, form, formset, change):
        instances = formset.save()
        for instance in instances:
            if isinstance(instance, GovernmentAttachment):
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


class GovernmentSupplyItemAdmin(RestrictedEditAdmin):
    list_display = ('intervention', 'title', 'unit_number', 'unit_price', 'provided_by')
    list_select_related = ('intervention',)
    list_filter = ('provided_by',)
    search_fields = ('title',)


admin.site.register(GovIntervention, GovInterventionAdmin)
admin.site.register(GovernmentAmendment, GovernmentAmendmentsAdmin)
admin.site.register(GovernmentResultLink, GovernmentResultsLinkAdmin)
admin.site.register(GovernmentBudget, GovernmentBudgetAdmin)
admin.site.register(GovernmentPlannedVisits, GovernmentPlannedVisitsAdmin)
admin.site.register(GovernmentAttachment, GovernmentAttachmentAdmin)
admin.site.register(GovernmentSupplyItem, GovernmentSupplyItemAdmin)

