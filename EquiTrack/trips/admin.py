__author__ = 'jcranwellward'

from django.contrib import admin
from django.forms import ModelForm
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.generic import GenericTabularInline

from reversion import VersionAdmin
from suit_ckeditor.widgets import CKEditorWidget

from locations.models import LinkedLocation
from .models import (
    TripReport,
    ActionPoint,
    TravelRoutes,
)

User = get_user_model()


class TravelRoutesInlineAdmin(admin.TabularInline):
    model = TravelRoutes


class ActionPointInlineAdmin(admin.TabularInline):
    model = ActionPoint


class SitesVisitedInlineAdmin(GenericTabularInline):
    model = LinkedLocation


class TripReportForm(ModelForm):
    class Meta:
        widgets = {
            'main_observations':
                CKEditorWidget(editor_options={'startupFocus': False})
        }


class TripReportAdmin(VersionAdmin):
    form = TripReportForm
    inlines = (
        TravelRoutesInlineAdmin,
        SitesVisitedInlineAdmin,
        ActionPointInlineAdmin,
    )
    list_display = (
        u'purpose_of_travel',
        u'activities_to_undertake',
        u'from_date',
        u'to_date',
        u'supervisor',
        u'status',
        u'approved_date',
    )
    filter_horizontal = (u'pcas',)
    fieldsets = (
        (u'Info', {
            u'fields':
                (u'purpose_of_travel',
                 u'activities_to_undertake',
                 u'from_date',
                 u'to_date',
                 u'pcas',
                 u'supervisor',
                 u'status',
                 u'approved_date',)
        }),
        (u'Report', {
            u'classes': (u'full-width',),
            u'fields': (u'main_observations',),
        }),
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
        Only show Activities for the chosen Sector
        """
        if db_field.rel.to is User:
            kwargs['queryset'] = User.objects.exclude(id=request.user.id)
        return super(TripReportAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    def get_readonly_fields(self, request, report=None):
        """
        Only let the supervisor of the report change report state
        """
        if report and request.user != report.supervisor:
            return ['status', 'approved_date']
        return []


admin.site.register(TripReport, TripReportAdmin)
