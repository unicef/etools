__author__ = 'jcranwellward'

from django.contrib import admin
from django.contrib import messages
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.generic import GenericTabularInline

from reversion import VersionAdmin
from import_export.admin import ExportMixin
from generic_links.admin import GenericLinkStackedInline
from messages_extends import constants as constants_messages

from locations.models import LinkedLocation
from .models import (
    Trip,
    Office,
    TripFunds,
    ActionPoint,
    TravelRoutes,
    FileAttachment
)
from .forms import (
    TripForm,
    TravelRoutesForm
)
from .exports import TripResource

User = get_user_model()


class TravelRoutesInlineAdmin(admin.TabularInline):
    model = TravelRoutes
    form = TravelRoutesForm
    suit_classes = u'suit-tab suit-tab-planning'
    verbose_name = u'Travel Itinerary'
    extra = 5


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
    extra = 5


class FileAttachmentInlineAdmin(GenericTabularInline):
    model = FileAttachment
    suit_classes = u'suit-tab suit-tab-attachments'


class LinksInlineAdmin(GenericLinkStackedInline):
    suit_classes = u'suit-tab suit-tab-attachments'
    extra = 1


class TripReportAdmin(ExportMixin, VersionAdmin):
    resource_class = TripResource
    save_as = True #TODO: There is a bug using this
    form = TripForm
    inlines = (
        TravelRoutesInlineAdmin,
        TripFundsInlineAdmin,
        SitesVisitedInlineAdmin,
        ActionPointInlineAdmin,
        FileAttachmentInlineAdmin,
        LinksInlineAdmin,
    )
    ordering = (u'-created_date',)
    date_hierarchy = u'from_date'
    list_display = (
        u'reference',
        u'created_date',
        u'purpose_of_travel',
        u'owner',
        u'section',
        u'office',
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
        u'office',
        u'from_date',
        u'to_date',
        u'no_pca',
        u'international_travel',
        u'supervisor',
        u'status',
        u'approved_date',
    )
    filter_vertical = (
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
                ((u'status', u'cancelled_reason'),
                 u'owner',
                 u'supervisor',
                 (u'section', u'office',),
                 (u'purpose_of_travel', u'monitoring_supply_delivery',),
                 (u'from_date', u'to_date',),
                 (u'travel_type', u'travel_assistant',),
                 u'approved_by_human_resources',
                 u'ta_required',
                 u'budget_owner',
                 u'programme_assistant',
                 (u'international_travel', u'representative',),
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
                 (u'representative_approval', u'date_representative_approved',),
                 u'approved_date',),
        }),
        (u'Travel/Admin', {
            u'classes': (u'suit-tab suit-tab-planning',),
            u'fields':
                (u'transport_booked',
                 u'security_granted',
                 u'ta_drafted',
                 u'ta_reference',
                 u'ta_drafted_date',
                 u'vision_approver',),
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

    def get_readonly_fields(self, request, trip=None):
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
            u'representative_approval',
            u'date_representative_approved',
            u'approved_date'
        ]

        if trip and request.user in [
            trip.owner,
            trip.travel_assistant
        ]:
            if trip.status == trip.APPROVED:
                fields.remove(u'status')

        if trip and request.user == trip.supervisor:
            if u'status' in fields:
                fields.remove(u'status')
            fields.remove(u'approved_by_supervisor')
            fields.remove(u'date_supervisor_approved')

        if trip and request.user == trip.budget_owner:
            fields.remove(u'approved_by_budget_owner')
            fields.remove(u'date_budget_owner_approved')

        hr_group, created = Group.objects.get_or_create(
            name=u'Human Resources'
        )
        if trip and hr_group in request.user.groups.all():
            fields.remove(u'human_resources')
            fields.remove(u'approved_by_human_resources')
            fields.remove(u'date_human_resources_approved')

        rep_group, created = Group.objects.get_or_create(
            name=u'Representative Office'
        )
        if trip and rep_group in request.user.groups.all():
            if u'status' in fields:
                fields.remove(u'status')
            fields.remove(u'representative_approval')
            fields.remove(u'date_representative_approved')

        if trip and request.user.is_superuser:
            return []

        return fields

    def save_model(self, request, obj, form, change):

        user = obj.owner
        url = 'http://{}{}'.format(
            Site.objects.get_current().domain,
            obj.get_admin_url()
        )
        status = "Trip {} for {} has been {}: {}".format(
            obj.reference(),
            obj.owner.get_full_name(),
            obj.status,
            url
        )

        messages.add_message(
            request,
            constants_messages.INFO_PERSISTENT,
            status,
            user=user
        )

        if obj.status == Trip.SUBMITTED:
            user = obj.supervisor
            status = 'Please approve the trip for {}: {}'.format(
                obj.owner.get_full_name(),
                url
            )

            messages.add_message(
                request,
                constants_messages.INFO_PERSISTENT,
                status,
                user=user
            )

        elif obj.status == Trip.APPROVED:

            if obj.travel_assistant and not obj.transport_booked:
                user = obj.travel_assistant
                status = 'Please book the transport for trip: {}'.format(
                    url
                )

                messages.add_message(
                    request,
                    constants_messages.INFO_PERSISTENT,
                    status,
                    user=user
                )

            if obj.ta_required and obj.programme_assistant and not obj.ta_drafted:
                user = obj.programme_assistant
                status = 'Please draft the TA for trip: {}'.format(
                    url
                )

                messages.add_message(
                    request,
                    constants_messages.INFO_PERSISTENT,
                    status,
                    user=user
                )

            if obj.ta_drafted and obj.vision_approver:
                user = obj.vision_approver
                status = 'Please approve the TA for trip: {}'.format(
                    url
                )

                messages.add_message(
                    request,
                    constants_messages.INFO_PERSISTENT,
                    status,
                    user=user
                )

        super(TripReportAdmin, self).save_model(request, obj, form, change)

    # def change_view(self, request, object_id, form_url='', extra_context=None):
    #
    #     try:
    #         return super(TripReportAdmin, self).change_view(request, object_id, form_url, extra_context)
    #     except IndexError:
    #
    #         request.POST['linkedlocation_set-TOTAL_FORMS'] = 0
    #
    #         return super(TripReportAdmin, self).change_view(request, object_id, form_url, extra_context)

    # def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
    #     if db_field.name == u'representative':
    #         rep_group = Group.objects.get(name=u'Representative Office')
    #         kwargs['queryset'] = rep_group.user_set.all()


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
    list_filter = (
        u'trip__owner',
        u'trip__supervisor',
        u'closed',
    )
    search_fields = (
        u'trip__name',
        u'description',
        u'actions_taken',
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

    def get_readonly_fields(self, request, obj=None):

        readonly_fields = [
            u'trip',
            u'description',
            u'due_date',
            u'persons_responsible',
            u'comments',
            u'closed',
        ]

        if obj and obj.trip.supervisor == request.user:
            readonly_fields.remove(u'comments')
            readonly_fields.remove(u'closed')

        return readonly_fields
    #
    # def save_model(self, request, obj, form, change):
    #     messages.add_message(
    #         request,
    #         constants_messages.INFO_PERSISTENT,
    #         "Hola abc desde test",
    #         user=request.user
    #     )


admin.site.register(Office)
admin.site.register(Trip, TripReportAdmin)
admin.site.register(ActionPoint, ActionPointsAdmin)