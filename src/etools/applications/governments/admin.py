from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models as django_models
from django.forms import SelectMultiple
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from admin_extra_urls.mixins import ExtraUrlMixin
from django_tenants.postgresql_backend.base import FakeTenant
from unicef_attachments.admin import AttachmentSingleInline
from unicef_attachments.models import Attachment
from unicef_snapshot.admin import ActivityInline, SnapshotModelAdmin

from etools.applications.governments import models
from etools.applications.partners.mixins import CountryUsersAdminMixin, HiddenPartnerMixin
from etools.libraries.djangolib.admin import RestrictedEditAdmin, RestrictedEditAdminMixin


class GovernmentReviewInlineAdmin(RestrictedEditAdminMixin, admin.TabularInline):
    model = models.GDDReview
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
    code = 'government_gdd_amendment_signed'


class GovernmentAmendmentPRCReviewInline(AttachmentSingleInline):
    verbose_name_plural = _("PRC Reviewed Attachment")
    code = 'government_gdd_amendment_internal_prc_review'


class GovernmentAmendmentsAdmin(AttachmentInlineAdminMixin, CountryUsersAdminMixin, RestrictedEditAdmin):
    staff_only = False
    model = models.GDDAmendment
    readonly_fields = [
        'amendment_number',
    ]
    raw_id_fields = [
        'gdd',
        'amended_gdd',
        'unicef_signatory',
        'partner_authorized_officer_signatory',
    ]

    list_display = (
        'gdd',
        'types',
        'signed_date'
    )
    search_fields = ('gdd__number', )
    list_filter = (
        'gdd',
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
        if obj and obj.status == models.GDD.ACTIVE:
            return self.max_num

        return 0


class GovernmentBudgetAdmin(RestrictedEditAdmin):
    model = models.GDDBudget
    fields = (
        'gdd',
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
        'gdd',
        'total'
    )
    list_filter = (
        'gdd',
    )
    search_fields = (
        'gdd__number',
    )
    readonly_fields = ('total', )
    extra = 0


class GovernmentPlannedVisitsAdmin(RestrictedEditAdmin):
    model = models.GDDPlannedVisits
    fields = (
        'gdd',
        'year',
        'programmatic_q1',
        'programmatic_q2',
        'programmatic_q3',
        'programmatic_q4',
    )
    search_fields = (
        'gdd__number',
    )
    list_display = (
        'gdd',
        'year',
        'programmatic_q1',
        'programmatic_q2',
        'programmatic_q3',
        'programmatic_q4',
    )


class GovernmentPlannedVisitsInline(RestrictedEditAdminMixin, admin.TabularInline):
    model = models.GDDPlannedVisits
    fields = (
        'gdd',
        'year',
        'programmatic_q1',
        'programmatic_q2',
        'programmatic_q3',
        'programmatic_q4',
    )
    extra = 0


class AttachmentFileInline(AttachmentSingleInline):
    verbose_name_plural = _("Attachment")
    code = 'government_gdd_attachment'


class GovernmentAttachmentAdmin(AttachmentInlineAdminMixin, RestrictedEditAdmin):
    model = models.GDDAttachment
    list_display = (
        'gdd',
        'type',
    )
    list_filter = (
        'gdd',
    )
    fields = (
        'gdd',
        'type',
    )
    inlines = [
        AttachmentFileInline,
    ]


class GovernmentAttachmentsInline(RestrictedEditAdminMixin, admin.TabularInline):
    model = models.GDDAttachment
    fields = ('type',)
    extra = 0
    code = 'government_gdd_attachment'

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.code = self.code
        return formset


class GovernmentResultsLinkAdmin(RestrictedEditAdmin):

    model = models.GDDResultLink
    fields = (
        'gdd',
        'cp_output',
        'ram_indicators'
    )
    list_display = (
        'gdd',
        'cp_output',
    )
    list_filter = (
        'gdd',
        'cp_output',
    )
    search_fields = (
        'gdd__title',
    )
    formfield_overrides = {
        django_models.ManyToManyField: {'widget': SelectMultiple(attrs={'size': '5', 'style': 'width:100%'})},
    }


class PRCReviewAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = _("Review Document by PRC")
    code = 'government_gdd_prc_review'


class SignedPDAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = _("Signed PD Document")
    code = 'government_gdd_signed_pd'


class GDDAdmin(
        ExtraUrlMixin,
        AttachmentInlineAdminMixin,
        CountryUsersAdminMixin,
        HiddenPartnerMixin,
        RestrictedEditAdminMixin,
        SnapshotModelAdmin
):
    model = models.GDD

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
        (_('GDD Details'), {
            'fields':
                (
                    'agreement',
                    'partner_organization',
                    'in_amendment',
                    'number',
                    'reference_number_year',
                    'title',
                    'status',
                    'country_programme',
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

    def created_date(self, obj):
        return obj.created_at.strftime('%d-%m-%Y')

    created_date.admin_order_field = '-created'

    def section_names(self, obj):
        return ' '.join([section.name for section in obj.sections.all()])

    section_names.short_description = "Sections"

    def has_module_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name='Country Office Administrator').exists()

    def attachments_link(self, obj):
        # url = "{}?gdd__id__exact={}".format(
        #     reverse("admin:government_gddattachment_changelist"),
        #     obj.pk
        # )
        # // TODO: fix links to attachments
        url = "TODO"
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
            if isinstance(instance, models.GDDAttachment):
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
    list_display = ('gdd', 'title', 'unit_number', 'unit_price', 'provided_by')
    list_select_related = ('gdd',)
    list_filter = ('provided_by',)
    search_fields = ('title',)


admin.site.register(models.GDD, GDDAdmin)
admin.site.register(models.GDDAmendment, GovernmentAmendmentsAdmin)
admin.site.register(models.GDDResultLink, GovernmentResultsLinkAdmin)
admin.site.register(models.GDDBudget, GovernmentBudgetAdmin)
admin.site.register(models.GDDPlannedVisits, GovernmentPlannedVisitsAdmin)
admin.site.register(models.GDDAttachment, GovernmentAttachmentAdmin)
admin.site.register(models.GDDSupplyItem, GovernmentSupplyItemAdmin)
admin.site.register(models.GDDKeyIntervention)
admin.site.register(models.GDDActivity)
admin.site.register(models.GDDActivityItem)
admin.site.register(models.EWPActivity)
