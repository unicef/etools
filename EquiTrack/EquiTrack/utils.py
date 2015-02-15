"""
Base classes and utility functions for EquiTrack apps
"""
__author__ = 'jcranwellward'

import tablib

from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.utils.datastructures import SortedDict

from import_export.resources import ModelResource
from post_office.models import EmailTemplate
from post_office import mail

from .mixins import AdminURLMixin


def send_mail(sender, template, variables, *recipients):
    mail.send(
        [recp for recp in recipients],
        sender,
        template=template,
        context=variables,
    )


class BaseEmail(object):

    template_name = None
    description = None
    subject = None
    content = None

    def __init__(self, object):
        self.object = object

    @classmethod
    def get_current_site(cls):
        return Site.objects.get_current()

    @classmethod
    def get_email_template(cls):
        if cls.template_name is None:
            raise NotImplemented()
        try:
            template = EmailTemplate.objects.get(
                name=cls.template_name
            )
        except EmailTemplate.DoesNotExist:
            template = EmailTemplate.objects.create(
                name=cls.template_name,
                description=cls.description,
                subject=cls.subject,
                content=cls.content
            )
        return template

    def get_context(self):
        raise NotImplemented()

    def send(self, sender, *recipients):

        send_mail(
            sender,
            self.get_email_template(),
            self.get_context(),
            *recipients
        )


def get_changeform_link(model, link_name='View', action='change'):
    if model.id:
        url_name = AdminURLMixin.admin_url_name.format(
            app_label=model._meta.app_label,
            model_name=model._meta.model_name,
            action=action
        )
        changeform_url = reverse(url_name, args=(model.id,))
        return u'<a class="btn btn-primary default" ' \
               u'onclick="return showAddAnotherPopup(this);" ' \
               u'href="{}" target="_blank">{}</a>'.format(changeform_url, link_name)
    return u''


class BaseExportResource(ModelResource):

    headers = []

    def insert_column(self, row, field_name, value):

        row[field_name] = value if self.headers else ''

    def insert_columns_inplace(self, row, fields, after_column):

        keys = row.keys()
        before_column = None
        if after_column in row:
            index = keys.index(after_column)
            offset = index + 1
            if offset < len(row):
                before_column = keys[offset]

        for key, value in fields.items():
            if before_column:
                row.insert(offset, key, value)
                offset += 1
            else:
                row[key] = value

    def fill_row(self, resource, fields):
        """
        This performs the actual work of translating
        a model into a fields dictionary for exporting.]
        Inheriting classes must implement this.
        """
        return NotImplementedError()

    def export(self, queryset=None):
        """
        Exports a resource.
        """
        rows = []

        if queryset is None:
            queryset = self.get_queryset()

        fields = SortedDict()

        for resource in queryset.iterator():
            # first pass creates table shape
            self.fill_row(resource, fields)

        self.headers = fields

        # Iterate without the queryset cache, to avoid wasting memory when
        # exporting large datasets.
        for resource in queryset.iterator():
            # second pass creates rows from the known table shape
            row = fields.copy()

            self.fill_row(resource, row)

            rows.append(row)

        data = tablib.Dataset(headers=fields.keys())
        for row in rows:
            data.append(row.values())
        return data