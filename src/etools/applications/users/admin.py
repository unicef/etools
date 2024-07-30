import logging

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import helpers, widgets
from django.contrib.admin.options import csrf_protect_m, IS_POPUP_VAR, TO_FIELD_VAR
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import Group
from django.db import connection, router, transaction
from django.db.models.signals import post_save
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from admin_extra_urls.decorators import button
from admin_extra_urls.mixins import ExtraUrlMixin
from django_tenants.admin import TenantAdminMixin
from django_tenants.postgresql_backend.base import FakeTenant
from django_tenants.utils import get_public_schema_name
from unicef_snapshot.admin import ActivityInline, SnapshotModelAdmin

from etools.applications.funds.tasks import sync_all_delegated_frs, sync_country_delegated_fr
from etools.applications.hact.tasks import update_hact_for_country, update_hact_values
from etools.applications.organizations.models import Organization
from etools.applications.users.models import Country, Realm, StagedUser, User, UserProfile, WorkspaceCounter
from etools.applications.users.signals import sync_realms_to_prp_on_update
from etools.applications.users.tasks import sync_realms_to_prp
from etools.applications.vision.tasks import sync_handler, vision_sync_task
from etools.libraries.azure_graph_api.tasks import sync_user
from etools.libraries.djangolib.admin import RestrictedEditAdminMixin, RssRealmEditAdminMixin, XLSXImportMixin
from etools.libraries.djangolib.utils import temporary_disconnect_signal


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
        'organization',
        'office',
        'job_title',
        'post_title',
        'phone_number',
        'staff_id',
    ]
    search_fields = (
        'tenant_profile__office__name',
        'country__name',
        'user__email'
    )
    readonly_fields = (
        'user',
        'country',
    )

    autocomplete_fields = (
        'organization',
    )

    fk_name = 'user'

    def get_fields(self, request, obj=None):

        fields = super().get_fields(request, obj=obj)
        if not request.user.is_superuser and 'country_override' in fields:
            fields.remove('country_override')
        return fields

    def office(self, obj):
        return get_office(obj)


class ProfileAdmin(admin.ModelAdmin):
    fields = [
        'country',
        'country_override',
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
    search_fields = (
        'tenant_profile__office__name',
        'country__name',
        'user__email',
        'guid'
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
                country__in=request.user.profile.countries_available
            )
        return queryset

    def get_fields(self, request, obj=None):

        fields = super().get_fields(request, obj=obj)
        if not request.user.is_superuser and 'country_override' in fields:
            fields.remove('country_override')
        return fields

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


class RealmInline(admin.StackedInline):
    verbose_name_plural = "Realms in current country"

    model = Realm
    raw_id_fields = ('country', 'organization', 'group')
    extra = 0

    def get_queryset(self, request):
        if isinstance(connection.tenant, FakeTenant):
            return super().get_queryset(request)
        return super().get_queryset(request).filter(country=connection.tenant)

    def has_delete_permission(self, request, obj=None):
        return False


class UserAdminPlus(XLSXImportMixin, RssRealmEditAdminMixin, ExtraUrlMixin, UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('User Preferences'), {'fields': ('preferences', )}),
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', )

    inlines = [ProfileInline, RealmInline]
    readonly_fields = ('last_login', 'date_joined',)

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
    list_select_related = ('profile__country', 'profile__office')

    UserChangeForm.Meta.exclude = ('groups',)

    title = _("Import LastMile users")
    import_field_mapping = {
        'Email address': 'email',
        'First Name': 'first_name',
        'Last Name': 'last_name',
        'IP Number': 'vendor_number',
        'Designation': 'job_title'
    }

    def has_import_permission(self, request):
        return request.user.email in settings.ADMIN_EDIT_EMAILS

    @transaction.atomic
    def import_data(self, workbook):
        sheet = workbook.active
        user_list = []
        for row in range(1, sheet.max_row):
            user_dict = {}
            for col in sheet.iter_cols(1, sheet.max_column):
                if col[0].value not in self.get_import_columns() or not col[row].value:
                    continue

                value = str(col[row].value).strip()
                if col[0].value == 'Email address':
                    value = value.replace('mailto:', '').lower()

                user_dict[self.import_field_mapping[col[0].value]] = value
            if 'email' in user_dict and user_dict not in user_list:
                user_list.append(user_dict)

        for user_dict in user_list:
            user_dict['username'] = user_dict['email']
            try:
                vendor_number = user_dict.pop('vendor_number')
                organization = Organization.objects.get(vendor_number=vendor_number)
            except Organization.DoesNotExist:
                logging.error(f'Organization not found: {vendor_number}, skipping row.. ')
                continue

            user_obj, created = User.objects.base_qs().update_or_create(
                email=user_dict['email'],
                username=user_dict['username'],
                defaults={'first_name': user_dict.get('first_name', 'Invalid First Name'),
                          'last_name': user_dict.get('last_name', 'Invalid Last Name')})

            if created:
                job_title = user_dict.pop('job_title')
                user_obj.profile.organization = organization
                user_obj.profile.job_title = job_title
                user_obj.profile.country = connection.tenant
                user_obj.profile.save(update_fields=['organization', 'job_title', 'country'])

            with temporary_disconnect_signal(post_save, sync_realms_to_prp_on_update, Realm):
                Realm.objects.update_or_create(
                    user=user_obj,
                    country=connection.tenant,
                    organization=organization,
                    group=Group.objects.get(name='IP LM Editor'),
                    defaults={'is_active': True}
                )

    @button(label="Sync User", permission='auth.change_user', details=False)
    def sync_user(self, request, pk):
        user = get_object_or_404(get_user_model(), pk=pk)
        sync_user.delay(user.username)
        return HttpResponseRedirect(reverse('admin:users_user_change', args=[user.pk]))

    @button(label="Sync Realms to PRP", permission='auth.change_user', details=False)
    def sync_realms_to_prp(self, request, pk):
        user = get_object_or_404(get_user_model(), pk=pk)
        sync_realms_to_prp.delay(user.id, timezone.now().timestamp())
        return HttpResponseRedirect(reverse('admin:users_user_change', args=[user.pk]))

    @button(label="Ad", permission='auth.change_user', details=False)
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
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(
                is_staff=True,
                profile__country=request.tenant
            )
        return queryset

    def get_readonly_fields(self, request, obj=None):
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
    search_fields = ('name', )

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


class MultipleRealmForm(forms.ModelForm):
    user = forms.ModelMultipleChoiceField(
        widget=widgets.ManyToManyRawIdWidget(Realm._meta.get_field("user").remote_field, admin.site),
        queryset=get_user_model().objects.all())
    country = forms.ModelMultipleChoiceField(
        widget=widgets.ManyToManyRawIdWidget(Realm._meta.get_field("country").remote_field, admin.site),
        queryset=Country.objects.all())
    group = forms.ModelMultipleChoiceField(
        widget=widgets.ManyToManyRawIdWidget(Realm._meta.get_field("group").remote_field, admin.site),
        queryset=Group.objects.all())
    organization = forms.ModelChoiceField(
        widget=widgets.ForeignKeyRawIdWidget(Realm._meta.get_field("organization").remote_field, admin.site),
        queryset=Organization.objects.all())

    class Meta:
        model = Realm
        fields = ['user', 'country', 'group', 'organization']


class RealmAdmin(RssRealmEditAdminMixin, SnapshotModelAdmin):
    change_list_template = "admin/users/realm/change_list.html"

    raw_id_fields = ('user', 'organization')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'country__name',
                     'organization__name', 'organization__vendor_number', 'group__name')
    autocomplete_fields = ('country', 'group')
    list_filter = ('country', 'group')

    inlines = (ActivityInline, )

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urlpatterns = super().get_urls()
        custom_urls = [
            path('multiple-realms/',
                 self.admin_site.admin_view(self.multiple_realms), name='multiple-realms'),
        ]
        return custom_urls + urlpatterns

    @csrf_protect_m
    def multiple_realms(self, request, obj=None, form_url='', extra_context=None):
        opts = self.model._meta
        app_label = opts.app_label
        if request.method == 'GET':
            fieldsets = [(None, {'fields': ['user', 'country', 'organization', 'group']})]
            initial = self.get_changeform_initial_data(request)
            form = MultipleRealmForm(initial=initial)
            admin_form = helpers.AdminForm(form, fieldsets, {}, model_admin=self)
            context = {
                **self.admin_site.each_context(request),
                'module_name': str(opts.verbose_name_plural),
                'has_add_permission': self.has_add_permission(request),
                'opts': opts,
                'app_label': app_label,
                'title': 'Add Multiple Realms',
                'media': self.media,
                'adminform': admin_form,
                'is_popup': IS_POPUP_VAR in request.POST or IS_POPUP_VAR in request.GET,
                'to_field': request.POST.get(TO_FIELD_VAR, request.GET.get(TO_FIELD_VAR)),
                'form_url': reverse('admin:multiple-realms', current_app=self.admin_site.name),
                **(extra_context or {}),
            }

            request.current_app = self.admin_site.name
            return TemplateResponse(request, 'admin/users/realm/add_multiple.html', context)

        if request.method == 'POST':
            if "_save_realms" in request.POST:
                user_ids = request.POST.get('user').split(',')
                country_ids = request.POST.get('country').split(',')
                organization_id = request.POST.get('organization')
                group_ids = request.POST.get('group').split(',')
                with transaction.atomic(using=router.db_for_write(self.model)):
                    for user_id in user_ids:
                        for country_id in country_ids:
                            for group_id in group_ids:
                                Realm.objects.update_or_create(
                                    user_id=user_id, country_id=country_id, organization_id=organization_id,
                                    group_id=group_id, defaults={'is_active': True})

            redirect_url = reverse('admin:%s_%s_changelist' %
                                   (opts.app_label, opts.model_name),
                                   current_app=self.admin_site.name)
            return HttpResponseRedirect(redirect_url)


class StagedUserAdmin(admin.ModelAdmin):
    list_display = ('country', 'organization', 'requester', 'reviewer', 'request_state')
    list_filter = ('request_state', 'country')
    search_fields = ('requester__email', 'requester__first_name', 'requester__last_name',
                     'reviewer__email', 'reviewer__first_name', 'reviewer__last_name',
                     'country__name', 'organization__name', 'organization__vendor_number')

    raw_id_fields = ('requester', 'reviewer', 'organization')

    def has_change_permission(self, request, obj=None):
        return False


# Re-register UserAdmin
admin.site.register(get_user_model(), UserAdminPlus)
admin.site.register(UserProfile, ProfileAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(WorkspaceCounter)
admin.site.register(Realm, RealmAdmin)
admin.site.register(StagedUser, StagedUserAdmin)
