__author__ = 'jcranwellward'

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import UserProfile, Country, Office, Section


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'
    fields = [
        'country',
        'country_override',
        'countries_available',
        'office',
        'section',
        'job_title',
        'phone_number',
    ]
    filter_horizontal = (
        'countries_available',
    )
    search_fields = (
        u'office__name',
        u'country__name',
        u'user__email'
    )
    readonly_fields = (
        u'user',
        u'country',
    )

    def get_fields(self, request, obj=None):

        fields = super(ProfileInline, self).get_fields(request, obj=obj)
        if not request.user.is_superuser and u'country_override' in fields:
            fields.remove(u'country_override')
        return fields

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):

        if db_field.name == u'countries_available':
            if request and request.user.is_superuser:
                kwargs['queryset'] = Country.objects.all()
            else:
                kwargs['queryset'] = request.user.profile.countries_available.all()

        return super(ProfileInline, self).formfield_for_manytomany(
            db_field, request, **kwargs
        )


class ProfileAdmin(admin.ModelAdmin):
    fields = [
        'country',
        'country_override',
        'countries_available',
        'office',
        'section',
        'job_title',
        'phone_number',
        'staff_id',
        'org_unit_code',
        'org_unit_name',
        'post_number',
        'post_title',
        'vendor_number',
        'section_code'

    ]
    list_display = (
        'username',
        'office',
        'section',
        'job_title',
        'phone_number',
    )
    list_editable = (
        'office',
        'section',
        'job_title',
        'phone_number',
    )
    list_filter = (
        'country',
        'office',
    )
    filter_horizontal = (
        'countries_available',
    )
    search_fields = (
        u'office__name',
        u'country__name',
        u'user__email'
    )
    readonly_fields = (
        u'user',
        u'country',
    )
    suit_form_includes = (
        ('users/supervisor.html', ),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        """
        You should only be able to manage users in the countries you have access to
        :param request:
        :return:
        """
        queryset = super(ProfileAdmin, self).get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(
                user__is_staff=True,
                country__in=request.user.profile.countries_available.all()
            )
        return queryset

    def get_fields(self, request, obj=None):

        fields = super(ProfileAdmin, self).get_fields(request, obj=obj)
        if not request.user.is_superuser and u'country_override' in fields:
            fields.remove(u'country_override')
        return fields

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):

        if db_field.name == u'countries_available':
            if request and request.user.is_superuser:
                kwargs['queryset'] = Country.objects.all()
            else:
                kwargs['queryset'] = request.user.profile.countries_available.all()

        return super(ProfileAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs
        )

    def save_model(self, request, obj, form, change):
        if 'supervisor' in form.data:
            supervisor = User.objects.get(id=int(form.data['supervisor'])).profile
            obj.supervisor = supervisor
        if 'oic' in form.data:
            oic = User.objects.get(id=int(form.data['oic'])).profile
            obj.oic = oic
        obj.save()

class UserAdminPlus(UserAdmin):

    inlines = [ProfileInline]

    list_display = [
        'email',
        'first_name',
        'last_name',
        'office',
        'is_staff',
        'is_active',
    ]

    def office(self, obj):
        return obj.profile.office

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        """
        You should only be able to manage users in your country
        :param request:
        :return:
        """
        queryset = super(UserAdminPlus, self).get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(
                is_staff=True,
                profile__country=request.tenant
            )
        return queryset

    def get_readonly_fields(self, request, obj=None):
        """
        You shouldnt be able grant superuser access if you are not a superuser
        :param request:
        :param obj:
        :return:
        """
        fields = list(super(UserAdminPlus, self).get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            fields.append(u'is_superuser')
        return fields


class CountryAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    list_display = (
        'name',
        'country_short_code',
        'business_area_code',
        'vision_sync_enabled',
        'vision_last_synced',
    )
    readonly_fields = (
        'vision_last_synced',
    )
    filter_horizontal = (
        'offices',
        'sections',
    )

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdminPlus)
admin.site.register(UserProfile, ProfileAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(Office)
admin.site.register(Section)

