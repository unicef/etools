from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db import connection
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse

from admin_extra_urls.decorators import button
from admin_extra_urls.mixins import ExtraUrlMixin
from django_tenants.admin import TenantAdminMixin
from django_tenants.utils import get_public_schema_name

from etools.applications.funds.tasks import sync_all_delegated_frs, sync_country_delegated_fr
from etools.applications.hact.tasks import update_hact_for_country, update_hact_values
from etools.applications.users.models import Country, UserProfile, WorkspaceCounter, Realm
from etools.applications.vision.tasks import sync_handler, vision_sync_task
from etools.libraries.azure_graph_api.tasks import sync_user


def get_office(obj):
    if connection.tenant.schema_name == get_public_schema_name():
        return None
    try:
        return obj.profile.tenant_profile.office
    except AttributeError:
        return None


class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
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
        'tenant_profile__office__name',
        'country__name',
        'user__email'
    )
    readonly_fields = (
        'user',
        'country',
    )

    fk_name = 'user'

    def get_fields(self, request, obj=None):

        fields = super().get_fields(request, obj=obj)
        if not request.user.is_superuser and 'country_override' in fields:
            fields.remove('country_override')
        return fields

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):

        if db_field.name == 'countries_available':
            if request and request.user.is_superuser:
                kwargs['queryset'] = Country.objects.all()
            else:
                kwargs['queryset'] = request.user.profile.countries_available.all()

        return super().formfield_for_manytomany(
            db_field, request, **kwargs
        )

    def office(self, obj):
        return get_office(obj)


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
        'country'
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
        'tenant_profile__office__name',
        'country__name',
        'user__email'
    )
    readonly_fields = (
        'user',
        'country',
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
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(
                user__is_staff=True,
                country__in=request.user.profile.countries_available.all()
            )
        return queryset

    def get_fields(self, request, obj=None):

        fields = super().get_fields(request, obj=obj)
        if not request.user.is_superuser and 'country_override' in fields:
            fields.remove('country_override')
        return fields

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):

        if db_field.name == 'countries_available':
            if request and request.user.is_superuser:
                kwargs['queryset'] = Country.objects.all()
            else:
                kwargs['queryset'] = request.user.profile.countries_available.all()

        return super().formfield_for_manytomany(
            db_field, request, **kwargs
        )

    def office(self, obj):
        return get_office(obj)

    def save_model(self, request, obj, form, change):
        if form.data.get('supervisor'):
            supervisor = get_user_model().objects.get(id=int(form.data['supervisor']))
            obj.supervisor = supervisor
        if form.data.get('oic'):
            oic = get_user_model().objects.get(id=int(form.data['oic']))
            obj.oic = oic
        obj.save()


class UserAdminPlus(ExtraUrlMixin, UserAdmin):
    inlines = [ProfileInline]
    readonly_fields = ('date_joined',)

    list_display = [
        'email',
        'first_name',
        'middle_name',
        'last_name',
        'office',
        'is_staff',
        'is_superuser',
        'is_active',
        'country',
    ]

    @button()
    def sync_user(self, request, pk):
        user = get_object_or_404(get_user_model(), pk=pk)
        sync_user.delay(user.username)
        return HttpResponseRedirect(reverse('admin:users_user_change', args=[user.pk]))

    @button()
    def ad(self, request, pk):
        user = get_object_or_404(get_user_model(), pk=pk)
        return HttpResponseRedirect(reverse('users_v3:ad-user-api-view', args=[user.email]))

    def country(self, obj):
        return obj.profile.country

    country.admin_order_field = 'profile__country'

    def office(self, obj):
        return get_office(obj)

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
        queryset = super().get_queryset(request)
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
        fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            fields.append('is_superuser')
        return fields


class CountryAdmin(ExtraUrlMixin, TenantAdminMixin, admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    list_display = (
        'name',
        'iso3_code',
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

    @button()
    def sync_fund_reservation_delegated(self, request, pk):
        country = Country.objects.get(pk=pk)
        if country.schema_name == get_public_schema_name():
            sync_all_delegated_frs.delay()
        else:
            sync_country_delegated_fr.delay(country.business_area_code)
        messages.info(request, "Task fund reservation delegated scheduled")
        return HttpResponseRedirect(reverse('admin:users_country_change', args=[country.pk]))

    @button()
    def sync_fund_reservation(self, request, pk):
        return self.execute_sync(pk, 'fund_reservation', request)

    @button()
    def sync_partners(self, request, pk):
        return self.execute_sync(pk, 'partner', request)

    @button()
    def sync_programme(self, request, pk):
        return self.execute_sync(pk, 'programme', request)

    @button()
    def sync_ram(self, request, pk):
        return self.execute_sync(pk, 'ram', request)

    @button()
    def sync_dct(self, request, pk):
        return self.execute_sync(pk, 'dct', request)

    @staticmethod
    def execute_sync(country_pk, synchronizer, request):
        country = Country.objects.get(pk=country_pk)
        if country.schema_name == get_public_schema_name():
            vision_sync_task(synchronizers=[synchronizer, ])
        else:
            sync_handler.delay(country.business_area_code, synchronizer)
        messages.info(request, f"Task {synchronizer} scheduled")
        return HttpResponseRedirect(reverse('admin:users_country_change', args=[country.pk]))

    @button()
    def update_hact(self, request, pk):
        country = Country.objects.get(pk=pk)
        if country.schema_name == get_public_schema_name():
            update_hact_values()
            messages.info(request, "HACT update has been scheduled for all countries")
        else:
            update_hact_for_country.delay(business_area_code=country.business_area_code)
            messages.info(request, "HACT update has been started for %s" % country.name)
        return HttpResponseRedirect(reverse('admin:users_country_change', args=[country.pk]))


# Re-register UserAdmin
admin.site.register(get_user_model(), UserAdminPlus)
admin.site.register(UserProfile, ProfileAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(WorkspaceCounter)
admin.site.register(Realm)
