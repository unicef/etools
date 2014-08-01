__author__ = 'jcranwellward'

import datetime

from django.contrib import admin
from django.forms import ModelForm, ValidationError
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.generic import GenericTabularInline

from reversion import VersionAdmin
from suit_ckeditor.widgets import CKEditorWidget
from generic_links.admin import GenericLinkStackedInline

from locations.models import LinkedLocation
from .models import (
    Trip,
    TripFunds,
    ActionPoint,
    TravelRoutes,
    FileAttachment
)

User = get_user_model()


class TravelRoutesForm(ModelForm):

    def clean(self):
        cleaned_data = super(TravelRoutesForm, self).clean()
        depart = cleaned_data.get('depart')
        arrive = cleaned_data.get('arrive')

        if arrive < depart:
            raise ValidationError(
                'Arrival must be greater than departure'
            )

        return cleaned_data


class TravelRoutesInlineAdmin(admin.TabularInline):
    model = TravelRoutes
    form = TravelRoutesForm
    suit_classes = u'suit-tab suit-tab-planning'
    verbose_name = u'Travel Itinerary'


class TripFundsInlineAdmin(admin.TabularInline):
    model = TripFunds
    suit_classes = u'suit-tab suit-tab-planning'
    extra = 3
    max_num = 3


class ActionPointInlineAdmin(admin.StackedInline):
    model = ActionPoint
    suit_classes = u'suit-tab suit-tab-reporting'
    filter_horizontal = (u'persons_responsible',)
    fields = (
        (u'description', u'due_date',),
        u'persons_responsible',
        (u'actions_taken', u'completed_date', u'comments', u'closed',),
    )

    def get_readonly_fields(self, request, report=None):
        """
        Only let certain users perform approvals
        """
        fields = [
            u'comments',
            u'closed'
        ]

        if report:
            if request.user == report.supervisor or request.user.is_superuser:
                return []

        return fields


class SitesVisitedInlineAdmin(GenericTabularInline):
    model = LinkedLocation
    suit_classes = u'suit-tab suit-tab-planning'
    verbose_name = u'Sites to visit'


class FileAttachmentInlineAdmin(GenericTabularInline):
    model = FileAttachment
    suit_classes = u'suit-tab suit-tab-attachments'


class LinksInlineAdmin(GenericLinkStackedInline):
    suit_classes = u'suit-tab suit-tab-attachments'


class TripForm(ModelForm):

    def clean(self):
        cleaned_data = super(TripForm, self).clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')
        owner = cleaned_data.get('owner')
        supervisor = cleaned_data.get('supervisor')
        ta_required = cleaned_data.get('ta_required')
        pcas = cleaned_data.get('pcas')
        no_pca = cleaned_data.get('no_pca')
        programme_assistant = cleaned_data.get(u'programme_assistant')
        approved_by_human_resources = cleaned_data.get(u'approved_by_human_resources')
        representative_approval = cleaned_data.get(u'representative_approval')

        if to_date < from_date:
            raise ValidationError('The to date must be greater than the from date')

        if owner == supervisor:
            raise ValidationError('You can\'t supervise your own trips')

        if not pcas and not no_pca:
            raise ValidationError(
                'You must select the PCAs related to this trip'
                ' or select the "Not related to a PCA" option'
            )

        if ta_required and not programme_assistant:
            raise ValidationError(
                'This trip needs a programme assistant '
                'to create a Travel Authorisation (TA)'
            )

        if self.instance:

            if self.instance.requires_hr_approval and not approved_by_human_resources:
                raise ValidationError(
                    'This trip needs HR approval'
                )

            if self.instance.requires_rep_approval and not representative_approval:
                raise ValidationError(
                    'This trip requires approval from the representative'
                )

        #TODO: this can be removed once we upgrade to 1.7
        return cleaned_data

    class Meta:
        model = Trip
        widgets = {
            'main_observations':
                CKEditorWidget(editor_options={'startupFocus': False})
        }


class TripReportAdmin(VersionAdmin):
    save_as = True
    form = TripForm
    inlines = (
        TravelRoutesInlineAdmin,
        TripFundsInlineAdmin,
        SitesVisitedInlineAdmin,
        ActionPointInlineAdmin,
        FileAttachmentInlineAdmin,
        LinksInlineAdmin,
    )
    list_display = (
        u'reference',
        u'purpose_of_travel',
        u'owner',
        u'section',
        u'from_date',
        u'to_date',
        u'supervisor',
        u'status',
        u'approved_date',
        u'outstanding_actions',
    )
    list_filter = (
        u'owner',
        u'section',
        u'from_date',
        u'to_date',
        u'supervisor',
        u'status',
        u'approved_date',
    )
    filter_horizontal = (
        u'pcas',
        u'partners',
    )
    readonly_fields = (
        u'reference',
    )
    fieldsets = (
        (u'Traveler', {
            u'classes': (u'suit-tab suit-tab-planning',),
            u'fields':
                (u'status',
                 u'owner',
                 u'supervisor',
                 u'budget_owner',
                 u'section',
                 (u'purpose_of_travel', u'monitoring_supply_delivery',),
                 (u'from_date', u'to_date',),
                 (u'travel_type', u'travel_assistant',),
                 u'international_travel',
                 u'no_pca',)
        }),
        (u'TA Details', {
            u'classes': (u'collapse', u'suit-tab suit-tab-planning',),
            u'fields':
                ((u'ta_required', u'programme_assistant',),),
        }),
        (u'PCA Details', {
            u'classes': (u'collapse', u'suit-tab suit-tab-planning',),
            u'fields':
                (u'pcas',
                 u'partners',),
        }),
        (u'Approval', {
            u'classes': (u'suit-tab suit-tab-planning',),
            u'fields':
                ((u'approved_by_supervisor', u'date_supervisor_approved',),
                 (u'approved_by_budget_owner', u'date_budget_owner_approved',),
                 (u'approved_by_human_resources', u'date_human_resources_approved', u'human_resources'),
                 (u'representative_approval', u'date_representative_approved', u'representative'),
                 u'approved_date',),
        }),
        (u'Travel/Admin', {
            u'classes': (u'suit-tab suit-tab-planning',),
            u'fields':
                (u'transport_booked',
                 u'security_granted',
                 u'ta_approved',
                 u'ta_reference',
                 u'ta_approved_date',),
        }),

        (u'Report', {
            u'classes': (u'suit-tab suit-tab-reporting', u'full-width',),
            u'fields': (
                u'main_observations',),
        }),
    )
    suit_form_tabs = (
        (u'planning', u'Planning'),
        (u'reporting', u'Reporting'),
        (u'attachments', u'Attachments')
    )

    def get_readonly_fields(self, request, report=None):
        """
        Only let certain users perform approvals
        """
        fields = [
            u'status',
            u'approved_by_supervisor',
            u'date_supervisor_approved'
            u'approved_by_budget_owner',
            u'date_budget_owner_approved',
            u'human_resources',
            u'approved_by_human_resources',
            u'date_human_resources_approved',
            u'representative',
            u'representative_approval',
            u'date_representative_approved',
            u'approved_date'
        ]

        if report and (request.user in [
            report.owner,
            report.supervisor,
            report.budget_owner,
        ] or request.user.is_superuser):
            return []

        return fields


class ActionPointsAdmin(admin.ModelAdmin):

    list_display = (
        u'trip',
        u'description',
        u'due_date',
    )

    def trip(self, obj):
        return unicode(obj.trip)

    def get_queryset(self, request):
        return ActionPoint.objects.filter(closed=False)


admin.site.register(Trip, TripReportAdmin)
admin.site.register(ActionPoint, ActionPointsAdmin)