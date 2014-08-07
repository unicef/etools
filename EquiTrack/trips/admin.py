__author__ = 'jcranwellward'

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.generic import GenericTabularInline

from reversion import VersionAdmin
from generic_links.admin import GenericLinkStackedInline

from locations.models import LinkedLocation
from .models import (
    Trip,
    TripFunds,
    ActionPoint,
    TravelRoutes,
    FileAttachment
)
from .forms import (
    TripForm,
    TravelRoutesForm
)

User = get_user_model()


class TravelRoutesInlineAdmin(admin.TabularInline):
    model = TravelRoutes
    form = TravelRoutesForm
    suit_classes = u'suit-tab suit-tab-planning'
    verbose_name = u'Travel Itinerary'
    extra = 2


class TripFundsInlineAdmin(admin.TabularInline):
    model = TripFunds
    suit_classes = u'suit-tab suit-tab-planning'
    extra = 3
    max_num = 3


class ActionPointInlineAdmin(admin.StackedInline):
    model = ActionPoint
    suit_classes = u'suit-tab suit-tab-reporting'
    filter_horizontal = (u'persons_responsible',)
    extra = 1
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
                 u'approved_by_human_resources',
                 (u'ta_required', u'programme_assistant',),
                 u'international_travel',
                 u'no_pca',)
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
                 (u'date_human_resources_approved', u'human_resources'),
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
                 u'ta_approved_date',
                 u'vision_approver',
                 u'vision_administrator'),
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
            u'date_supervisor_approved',
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
        u'responsible',
        u'actions_taken',
        u'supervisor',
        u'comments',
        u'closed',

    )
    readonly_fields = (
        u'trip',
        u'description',
        u'due_date',
        u'persons_responsible',
        u'comments',
        u'closed',
    )

    def trip(self, obj):
        return unicode(obj.trip)

    def supervisor(self, obj):
        return obj.trip.supervisor

    def responsible(self, obj):
        return ', '.join(
            [
                user.get_full_name()
                for user in
                obj.persons_responsible.all()
            ]
        )

    def has_add_permission(self, request):
        return False


admin.site.register(Trip, TripReportAdmin)
admin.site.register(ActionPoint, ActionPointsAdmin)