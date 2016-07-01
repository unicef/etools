__author__ = 'jcranwellward'

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models, connection
from django.forms import Textarea

from reversion.admin import VersionAdmin
from import_export.admin import ExportMixin
from generic_links.admin import GenericLinkStackedInline
from users.models import UserProfile

from EquiTrack.utils import get_changeform_link
from EquiTrack.mixins import CountryUsersAdminMixin
from EquiTrack.forms import AutoSizeTextForm, RequireOneFormSet
from users.models import Office, Section
from .models import (
    Trip,
    LinkedPartner,
    TripFunds,
    ActionPoint,
    TravelRoutes,
    FileAttachment,
    TripLocation,
)
from .forms import (
    TripForm,
    TripFundsForm,
    TripLocationForm,
    TravelRoutesForm,
    RequireOneLocationFormSet
)
from .filters import (
    TripReportFilter,
    PartnerFilter,
    SupervisorFilter,
    OwnerFilter
)
from reports.models import Result
from .exports import TripResource, ActionPointResource

User = get_user_model()


class LinkedPartnerInlineAdmin(admin.TabularInline):
    model = LinkedPartner
    suit_classes = u'suit-tab suit-tab-planning'
    extra = 1


class TravelRoutesInlineAdmin(admin.TabularInline):
    model = TravelRoutes
    form = TravelRoutesForm
    suit_classes = u'suit-tab suit-tab-planning'
    verbose_name = u'Travel Itinerary'
    extra = 5


class TripFundsInlineAdmin(admin.TabularInline):
    model = TripFunds
    formset = TripFundsForm
    suit_classes = u'suit-tab suit-tab-planning'
    extra = 3
    max_num = 3

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == u'result':
            kwargs['queryset'] = Result.objects.filter(result_type__name=u'Activity', hidden=False)

        return super(TripFundsInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class ActionPointInlineAdmin(CountryUsersAdminMixin, admin.StackedInline):
    model = ActionPoint
    form = AutoSizeTextForm
    suit_classes = u'suit-tab suit-tab-reporting'
    extra = 1
    fields = (
        (u'description', u'due_date',),
        u'person_responsible',
        (u'actions_taken',),
        (u'completed_date', u'status'),
        u'follow_up'
    )


class TripLocationsInlineAdmin(admin.TabularInline):
    model = TripLocation
    form = TripLocationForm
    formset = RequireOneLocationFormSet
    suit_classes = u'suit-tab suit-tab-planning'
    verbose_name = u'Sites to visit'
    fields = (
        'location',
    )


class FileAttachmentInlineAdmin(admin.TabularInline):
    model = FileAttachment
    suit_classes = u'suit-tab suit-tab-attachments'
    # make the textarea a little smaller by default. they can be extended if needed
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 40})},
    }
    fields = (u'type', u'caption', u'report')
    # get the number of extra fields (it looks to bulky with 3
    # if more are needed the "add another fileAttachment" appears
    extra = 1


class LinksInlineAdmin(GenericLinkStackedInline):
    suit_classes = u'suit-tab suit-tab-attachments'
    extra = 1


class TripReportAdmin(CountryUsersAdminMixin, ExportMixin, VersionAdmin):
    resource_class = TripResource
    save_as = True
    form = TripForm
    inlines = (
        LinkedPartnerInlineAdmin,
        TravelRoutesInlineAdmin,
        TripLocationsInlineAdmin,
        #TripFundsInlineAdmin,
        ActionPointInlineAdmin,
        FileAttachmentInlineAdmin,
        LinksInlineAdmin,
    )
    ordering = (u'-created_date',)
    date_hierarchy = u'from_date'
    search_fields = (
        u'owner__first_name',
        u'owner__email',
        u'owner__last_name',
        u'section__name',
        u'office__name',
        u'purpose_of_travel',
    )
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
        u'ta_required',
        u'ta_reference',
        u'approved_date',
        u'attachments',
        u'outstanding_actions',
        u'show_driver_trip',
    )
    list_filter = (
        (u'owner', admin.RelatedOnlyFieldListFilter),
        (u'supervisor', admin.RelatedOnlyFieldListFilter),
        (u'section', admin.RelatedOnlyFieldListFilter),
        (u'office', admin.RelatedOnlyFieldListFilter),
        u'from_date',
        u'to_date',
        u'travel_type',
        u'international_travel',
        (u'budget_owner', admin.RelatedOnlyFieldListFilter),
        u'status',
        u'approved_date',
        u'pending_ta_amendment',
        TripReportFilter,
        u'ta_trip_took_place_as_planned',
        PartnerFilter,
    )
    filter_vertical = (
        u'pcas',
        u'partners',
    )
    readonly_fields = (
        u'reference',
        u'show_driver_trip',
    )
    fieldsets = (
        (u'Traveler', {
            u'classes': (u'suit-tab suit-tab-planning',),
            u'fields':
                ((u'status', u'cancelled_reason'),
                 u'owner',
                 u'supervisor',
                 (u'section', u'office',),
                 (u'purpose_of_travel',),
                 (u'from_date', u'to_date',),
                 (u'travel_type', u'travel_assistant',),
                 u'security_clearance_required',
                 u'ta_required',
                 u'budget_owner',
                 u'programme_assistant',
                 (u'international_travel', u'representative',),
                 u'approved_by_human_resources',)
        }),
        # (u'Partnership Details', {
        #     u'classes': (u'suit-tab suit-tab-planning', u'collapse',),
        #     u'fields':
        #         (u'pcas',
        #          u'partners',),
        # }),
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
                (
                 (u'driver', u'driver_supervisor'),
                 u'transport_booked',
                 u'security_granted',
                 u'ta_drafted',
                 u'ta_reference',
                 u'ta_drafted_date',
                 u'vision_approver'),
        }),

        (u'Report', {
            u'classes': (u'suit-tab suit-tab-reporting', u'full-width',),
            u'fields': (
                u'main_observations',
            ),
        }),

        (u'Constraints/Challenges/Opportunities', {
            u'classes': (u'suit-tab suit-tab-reporting',),
            u'fields': (
                u'constraints',
                u'lessons_learned',
                u'opportunities',
            ),
        }),

        (u'Travel Certification', {
            u'classes': (u'suit-tab suit-tab-reporting',),
            u'fields': (
                u'ta_trip_took_place_as_planned',
                u'ta_trip_repay_travel_allowance',),
        }),
    )
    suit_form_tabs = (
        (u'planning', u'Planning'),
        (u'reporting', u'Reporting'),
        (u'attachments', u'Attachments'),
        (u'checklists', u'Checklists'),

    )

    suit_form_includes = (
        ('admin/trips/checklists-tab.html', 'top', 'checklists'),
    )

    def show_driver_trip(self, obj):
        if obj.driver_trip:
            return get_changeform_link(obj.driver_trip, link_name='View Driver Trip')
        return ''
    show_driver_trip.allow_tags = True
    show_driver_trip.short_description = 'Driver Trip'

    def save_formset(self, request, form, formset, change):
        """
        Override here to check if the itinerary has changed
        """
        for form in formset.forms:
            if form.has_changed():  #TODO: Test this
                if type(form.instance) is TravelRoutes and form.instance.trip.status == Trip.APPROVED:
                    trip = Trip.objects.get(pk=form.instance.trip.pk)
                    trip.status = Trip.SUBMITTED
                    trip.approved_by_supervisor = False
                    trip.date_supervisor_approved = None
                    trip.approved_by_budget_owner = False
                    trip.date_budget_owner_approved = None
                    trip.approved_by_human_resources = None
                    trip.representative_approval = None
                    trip.date_representative_approved = None
                    trip.approved_date = None
                    trip.approved_email_sent = False
                    trip.submitted_email_sent = False
                    trip.save()

        formset.save()

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

        if trip and trip.status == Trip.PLANNED and request.user in [
            trip.owner,
            trip.travel_assistant,
            trip.supervisor
        ]:
            fields.remove(u'status')

        if trip and trip.status == Trip.APPROVED and request.user in [
            trip.owner,
            trip.travel_assistant,
            trip.programme_assistant
        ]:
            fields.remove(u'status')

        if trip and request.user == trip.supervisor:
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
            fields.remove(u'representative_approval')
            fields.remove(u'date_representative_approved')

        return fields

    def get_form(self, request, obj=None, **kwargs):
        form = super(TripReportAdmin, self).get_form(request, obj, **kwargs)
        form.request = request
        try:
            user_profile = request.user.profile
            form.base_fields['owner'].initial = request.user
            form.base_fields['office'].initial = user_profile.office
            form.base_fields['section'].initial = user_profile.section
        except UserProfile.DoesNotExist:
            form.base_fields['owner'].initial = request.user
        return form

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):

        if db_field.name == u'representative':
            rep_group = Group.objects.get(name=u'Representative Office')
            kwargs['queryset'] = rep_group.user_set.filter(
                profile__country=connection.tenant,
                is_staff=True,
            )

        if db_field.name == u'driver':
            rep_group = Group.objects.get(name=u'Driver')
            kwargs['queryset'] = rep_group.user_set.filter(
                profile__country=connection.tenant,
                is_staff=True,
            )

        if db_field.rel.to is Office:
            kwargs['queryset'] = connection.tenant.offices.all()

        if db_field.rel.to is Section:
            kwargs['queryset'] = connection.tenant.sections.all()

        return super(TripReportAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class ActionPointsAdmin(CountryUsersAdminMixin, ExportMixin, admin.ModelAdmin):
    resource_class = ActionPointResource
    exclude = [u'persons_responsible']
    date_hierarchy = u'due_date'
    list_display = (
        u'trip',
        u'description',
        u'due_date',
        u'person_responsible',
        u'actions_taken',
        u'comments',
        u'status'
    )
    list_filter = (
        #(u'trip__owner', admin.RelatedOnlyFieldListFilter),
        (u'person_responsible', admin.RelatedOnlyFieldListFilter),
        u'status',
    )
    search_fields = (
        u'trip__name',
        u'description',
        u'actions_taken',
    )

    def trip(self, obj):
        return unicode(obj.trip)

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):

        readonly_fields = [
            u'trip',
            u'description',
            u'due_date',
            u'person_responsible',
            u'comments',
            u'status',
        ]

        if obj and obj.person_responsible == request.user:
            readonly_fields.remove(u'comments')
            readonly_fields.remove(u'status')

        return readonly_fields


admin.site.register(Trip, TripReportAdmin)
admin.site.register(ActionPoint, ActionPointsAdmin)
admin.site.register(TripLocation)
