import traceback

from django import forms
from django.conf import settings
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import ForeignKey, ManyToManyField, OneToOneField
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

import openpyxl

from etools.libraries.djangolib.models import EPOCH_ZERO


class AdminListMixin:
    exclude_fields = ['id', 'deleted_at']
    custom_fields = ['is_deleted']

    def __init__(self, model, admin_site):
        """
        Gather all the fields from model meta expect fields in 'exclude_fields'.
        Add all fields listed in 'custom_fields'. Those can be admin method, model methods etc.
        """
        self.list_display = [field.name for field in model._meta.fields if field.name not in self.exclude_fields]
        self.list_display += self.custom_fields
        self.search_fields = [field.name for field in model._meta.fields if isinstance(
            not field, (OneToOneField, ForeignKey, ManyToManyField)) and field.name not in self.exclude_fields]

        super().__init__(model, admin_site)

    def is_deleted(self, obj):
        """
        Display a deleted indicator on the admin page (green/red tick).
        """
        if hasattr(obj, "deleted_at"):
            return obj.deleted_at == EPOCH_ZERO

    is_deleted.short_description = 'Deleted'
    is_deleted.boolean = True


class RestrictedEditAdminMixin:
    def has_add_permission(self, request, obj=None):
        if not settings.RESTRICTED_ADMIN:
            return True
        return request.user.email in settings.ADMIN_EDIT_EMAILS

    def has_change_permission(self, request, obj=None):
        if not settings.RESTRICTED_ADMIN:
            return True
        return request.user.email in settings.ADMIN_EDIT_EMAILS

    def has_delete_permission(self, request, obj=None):
        if not settings.RESTRICTED_ADMIN:
            return True
        return request.user.email in settings.ADMIN_EDIT_EMAILS


class RestrictedEditAdmin(RestrictedEditAdminMixin, admin.ModelAdmin):
    pass


class RssRealmEditAdminMixin(RestrictedEditAdminMixin):

    def has_add_permission(self, request, obj=None):
        allowed = super().has_add_permission(request, obj=None)
        if allowed:
            return allowed

        if request.user.groups.filter(name='RSS').exists():
            return True
        return False

    def has_change_permission(self, request, obj=None):
        allowed = super().has_add_permission(request, obj=None)
        if allowed:
            return allowed

        if request.user.groups.filter(name='RSS').exists():
            return True
        return False


class ImportForm(forms.Form):
    import_file = forms.FileField(label=_('XLSX File to import'))


class XLSXImportMixin:
    """
    XLSX Import mixin.
    """
    change_list_template = 'admin/import/change_list_import.html'
    import_template_name = 'admin/import/import.html'
    import_field_mapping = {}

    def get_model_info(self):
        app_label = self.model._meta.app_label
        return app_label, self.model._meta.model_name,

    def has_import_permission(self, request):
        """
        Returns whether a request has import permission.
        """
        raise NotImplementedError

    def get_import_columns(self):
        """
        Returns which columns will be imported.
        """
        if not self.import_field_mapping:
            raise NotImplementedError('"import_field_mapping" dict structure was not defined')
        return self.import_field_mapping.keys()

    def get_urls(self):
        urls = super().get_urls()
        info = self.get_model_info()
        my_urls = [
            path('import/',
                 self.admin_site.admin_view(self.import_action),
                 name='%s_%s_import' % info),
        ]
        return my_urls + urls

    def get_import_form(self):
        """
        Get the form type used to read the import format and file.
        """
        return ImportForm

    def get_form_kwargs(self, form, *args, **kwargs):
        """
        Prepare/returns kwargs for the import form.
        """
        return kwargs

    def get_import_data_kwargs(self, request, *args, **kwargs):
        """
        Prepare kwargs for import_data.
        """
        form = kwargs.get('form')
        if form:
            kwargs.pop('form')
            return kwargs
        return {}

    def get_context(self, request, form):
        context = {}
        context.update(self.admin_site.each_context(request))
        context['title'] = self.title or _('Import')
        context['form'] = form
        context['opts'] = self.model._meta
        context['fields'] = self.import_field_mapping.keys()
        return context

    def import_action(self, request, *args, **kwargs):
        if not self.has_import_permission(request):
            raise PermissionDenied

        form_type = self.get_import_form()
        form_kwargs = self.get_form_kwargs(form_type, *args, **kwargs)
        form = form_type(request.POST or None, request.FILES or None, **form_kwargs)

        if request.POST and form.is_valid():
            import_file = form.cleaned_data['import_file']
            try:
                wb = openpyxl.load_workbook(import_file)
                self.import_data(wb)
                wb.close()
            except Exception:
                form._errors.update(
                    {'Import': _(" Error encountered while trying to import data from: %s " % import_file.name),
                     '|': traceback.format_exc()
                     })
                return TemplateResponse(request, [self.import_template_name], self.get_context(request, form))

            redirect_url = reverse('admin:%s_%s_changelist' % self.get_model_info(),
                                   current_app=self.admin_site.name)
            return HttpResponseRedirect(redirect_url)

        request.current_app = self.admin_site.name
        return TemplateResponse(request, [self.import_template_name], self.get_context(request, form))

    def import_data(self, workbook):
        raise NotImplementedError

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['has_import_permission'] = self.has_import_permission(request)
        return super().changelist_view(request, extra_context)
