__author__ = 'jcranwellward'

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from import_export import resources
from import_export.admin import ImportExportMixin

from .models import UserProfile, Country, Office, Section


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'


class UserResource(resources.ModelResource):

    class Meta:
        model = User


class UserAdminPlus(ImportExportMixin, UserAdmin):
    resource_class = UserResource

    def has_add_permission(self, request):
        return False
    
    def get_queryset(self, request):
        queryset = super(UserAdminPlus, self).get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(profile__country=request.tenant)
        return queryset


class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'country',
        'country_override',
        'office',
        'section',
        'job_title',
        'phone_number',
    )
    list_editable = (
        'country',
        'country_override',
        'office',
        'section',
        'job_title',
        'phone_number',
    )
    list_filter = (
        'country',
        'office',
        'user__email'
    )
    search_fields = (
        u'office__name',
        u'country__name',
        u'user__email'
    )


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdminPlus)
admin.site.register(UserProfile, ProfileAdmin)
admin.site.register(Country)
admin.site.register(Office)
admin.site.register(Section)

