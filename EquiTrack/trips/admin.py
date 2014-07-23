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
    ActionPoint,
    TravelRoutes,
    FileAttachment
)

User = get_user_model()


class TravelRoutesInlineAdmin(admin.TabularInline):
    model = TravelRoutes
    suit_classes = u'suit-tab suit-tab-planning'


class ActionPointInlineAdmin(admin.TabularInline):
    model = ActionPoint
    suit_classes = u'suit-tab suit-tab-reporting'

    def get_readonly_fields(self, request, report=None):
        """
        Only let certain users perform approvals
        """
        fields = [
            u'closed'
        ]

        if report:
            if request.user == report.supervisor or request.user.is_superuser:
                return []

        return fields


class SitesVisitedInlineAdmin(GenericTabularInline):
    model = LinkedLocation
    suit_classes = u'suit-tab suit-tab-planning'


class FileAttachmentInlineAdmin(GenericTabularInline):
    model = FileAttachment
    suit_classes = u'suit-tab suit-tab-attachments'


class LinksInlineAdmin(GenericLinkStackedInline):
    suit_classes = u'suit-tab suit-tab-attachments'


class TripForm(ModelForm):

    def clean(self):
        cleaned_data = super(TripForm, self).clean()
        trip_type = cleaned_data.get("trip_type")
        trip_status = cleaned_data.get("status")
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')
        owner = cleaned_data.get('owner')
        supervisor = cleaned_data.get('supervisor')
        ta_required = cleaned_data.get('ta_required')
        wbs = cleaned_data.get('wbs')
        grant = cleaned_data.get('wbs')
        pcas = cleaned_data.get('pcas')
        no_pca = cleaned_data.get('no_pca')
        international_travel = cleaned_data.get('international_travel')
        approved_by_budget_owner = cleaned_data.get('approved_by_budget_owner')
        approved_date = cleaned_data.get('approved_date')
        programme_assistant = cleaned_data.get(u'programme_assistant')
        approved_by_human_resources = cleaned_data.get(u'approved_by_human_resources')
        representative_approval = cleaned_data.get(u'representative_approval')

        if owner == supervisor:
            raise ValidationError('You cant supervise your own trips')

        if not pcas and not no_pca:
            raise ValidationError(
                'You must select the PCAs related to this trip'
                ' or select the "Not related to a PCA" option'
            )

        # trips over 10 hours need a TA, WBS and Grant for over night stay
        if ta_required:

            if not programme_assistant:
                raise ValidationError(
                    'This trip is greater than 10 hours and needs a '
                    'programme assistant to create a Travel Authorisation (TA)'
                )

            if not wbs:
                raise ValidationError(
                    'This trip is greater than 10 hours and needs a WBS'
                )

            if not grant:
                raise ValidationError(
                    'This trip is greater than 10 hours and needs a Grant'
                )

        if trip_status != Trip.APPROVED and self.instance.can_be_approved:
            cleaned_data['approved_date'] = datetime.datetime.today()
            cleaned_data['status'] = Trip.APPROVED


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
        u'wbs',
        u'grant',
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
                 u'purpose_of_travel',
                 (u'from_date', u'to_date',),
                 (u'travel_type', u'travel_assistant',),
                 u'international_travel',
                 u'no_pca',
                 (u'activities_undertaken',
                 u'monitoring_supply_delivery'))
        }),
        (u'Travel Authorisation', {
            u'classes': (u'collapse', u'wide',),
            u'fields':
                ((u'ta_required', u'programme_assistant',),
                 u'wbs',
                 u'grant',),
        }),
        (u'PCA Details', {
            u'classes': (u'collapse', u'wide',),
            u'fields':
                (u'pcas',
                 u'partners',),
        }),
        (u'Approval', {
            u'classes': (u'suit-tab suit-tab-planning',),
            u'fields':
                (u'approved_by_supervisor',
                 u'approved_by_budget_owner',
                 u'approved_by_human_resources',
                 u'representative_approval',
                 u'approved_date',),
        }),
        (u'Travel', {
            u'classes': (u'suit-tab suit-tab-planning',),
            u'fields':
                (u'transport_booked',
                 u'security_clearance',
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
            u'approved_by_budget_owner',
            u'approved_by_human_resources',
            u'representative_approval',
            u'approved_date'
        ]

        if report:
            if request.user == report.supervisor or request.user.is_superuser:
                return []

        return fields


admin.site.register(Trip, TripReportAdmin)
