from functools import update_wrapper

from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from tenant_schemas.utils import get_public_schema_name

from etools.applications.hact.tasks import update_hact_for_country, update_hact_values
from etools.applications.users.models import (
    Country,
    Office,
    UserProfile,
    WorkspaceCounter,
)
from etools.applications.vision.tasks import sync_handler, vision_sync_task
from etools.libraries.azure_graph_api.tasks import sync_user


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'
    fields = [
        'country',
        'country_override',
        'countries_available',
        'office',
        'job_title',
        'post_title',
        'phone_number',
        'staff_id',
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

    fk_name = 'user'

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
        'job_title',
        'phone_number',
        'staff_id',
        'org_unit_code',
        'org_unit_name',
        'post_number',
        'post_title',
        'vendor_number',
    ]
    list_display = (
        'username',
        'office',
        'job_title',
        'phone_number',
    )
    list_editable = (
        'office',
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
        if form.data.get('supervisor'):
            supervisor = get_user_model().objects.get(id=int(form.data['supervisor']))
            obj.supervisor = supervisor
        if form.data.get('oic'):
            oic = get_user_model().objects.get(id=int(form.data['oic']))
            obj.oic = oic
        obj.save()


class UserAdminPlus(UserAdmin):

    change_form_template = 'admin/users/user/change_form.html'
    inlines = [ProfileInline]
    readonly_fields = ('date_joined',)

    list_display = [
        'email',
        'first_name',
        'last_name',
        'office',
        'is_staff',
        'is_active',
    ]

    def get_urls(self):
        urls = super(UserAdminPlus, self).get_urls()

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        custom_urls = [
            url(r'^(?P<pk>\d+)/sync_user/$', wrap(self.sync_user), name='users_sync_user'),
        ]
        return custom_urls + urls

    def sync_user(self, request, pk):
        user = get_object_or_404(get_user_model(), pk=pk)
        sync_user.delay(user.username)
        return HttpResponseRedirect(reverse('admin:auth_user_change', args=[user.pk]))

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
    change_form_template = 'admin/users/country/change_form.html'

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
    )

    def get_urls(self):
        urls = super(CountryAdmin, self).get_urls()

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        custom_urls = [
            url(r'^(?P<pk>\d+)/sync_fc/$', wrap(self.sync_fund_commitment), name='users_country_fund_commitment'),
            url(r'^(?P<pk>\d+)/sync_fr/$', wrap(self.sync_fund_reservation), name='users_country_fund_reservation'),
            url(r'^(?P<pk>\d+)/sync_partners/$', wrap(self.sync_partners), name='users_country_partners'),
            url(r'^(?P<pk>\d+)/sync_programme/$', wrap(self.sync_programme), name='users_country_programme'),
            url(r'^(?P<pk>\d+)/sync_ram/$', wrap(self.sync_ram), name='users_country_ram'),
            url(r'^(?P<pk>\d+)/update_hact/$', wrap(self.update_hact), name='users_country_update_hact'),
        ]
        return custom_urls + urls

    def sync_fund_commitment(self, request, pk):
        return self.execute_sync(pk, 'fund_commitment')

    def sync_fund_reservation(self, request, pk):
        return self.execute_sync(pk, 'fund_reservation')

    def sync_partners(self, request, pk):
        return self.execute_sync(pk, 'partner')

    def sync_programme(self, request, pk):
        return self.execute_sync(pk, 'programme')

    def sync_ram(self, request, pk):
        return self.execute_sync(pk, 'ram')

    @staticmethod
    def execute_sync(country_pk, synchronizer):
        country = Country.objects.get(pk=country_pk)
        if country.schema_name == get_public_schema_name():
            vision_sync_task(synchronizers=[synchronizer, ])
        else:
            sync_handler.delay(country.name, synchronizer)
        return HttpResponseRedirect(reverse('admin:users_country_change', args=[country.pk]))

    def update_hact(self, request, pk):
        country = Country.objects.get(pk=pk)
        if country.schema_name == get_public_schema_name():
            update_hact_values()
            messages.info(request, "HACT update has been scheduled for all countries")
        else:
            update_hact_for_country.delay(country_name=country.name)
            messages.info(request, "HACT update has been started for %s" % country.name)
        return HttpResponseRedirect(reverse('admin:users_country_change', args=[country.pk]))


# Re-register UserAdmin
admin.site.register(get_user_model(), UserAdminPlus)
admin.site.register(UserProfile, ProfileAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(Office)
admin.site.register(WorkspaceCounter)
