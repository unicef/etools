from __future__ import absolute_import, division, print_function, unicode_literals

import os

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, connection
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible
from django.utils.text import slugify
from django.utils.translation import ugettext as _
from future.backports.urllib.parse import urlsplit

from model_utils.models import TimeStampedModel
from ordered_model.models import OrderedModel


@python_2_unicode_compatible
class FileType(OrderedModel, models.Model):
    name = models.CharField(max_length=64, verbose_name=_('Name'))
    label = models.CharField(max_length=64, verbose_name=_('Label'))

    code = models.CharField(max_length=64, default="", verbose_name=_('Code'))

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ("name", "code", )
        ordering = ('code', 'order')


def generate_file_path(attachment, filename):
    # updating other models to use this function,
    # for now maintaining their previous upload
    # paths
    # TODO move all files to standard file path setup?
    app = attachment.content_type.app_label
    model_name = attachment.content_type.model
    obj_pk = str(attachment.object_id)
    obj = attachment.content_object

    if app == "partners":
        file_path = [
            connection.schema_name,
            'file_attachments',
            "partner_organization",
        ]
        if model_name == "agreement":
            file_path = file_path + [
                str(obj.partner.pk),
                "agreements",
                str(obj.agreement_number)
            ]
        elif model_name == "assessment":
            file_path = file_path + [
                str(obj.partner.pk),
                # maintain spelling mistake
                # until such time as files are moved
                # TODO move all files to standard file path setup?
                'assesments',
                obj_pk,
            ]
        elif model_name in [
                "interventionamendment",
                "interventionattachment"
        ]:
            file_path = file_path + [
                str(obj.intervention.agreement.partner.pk),
                'agreements',
                str(obj.intervention.agreement.pk),
                'interventions',
            ]
            if model_name == "interventionamendment":
                # this is an issue with the previous function
                # it has partner pk twice in the file path
                # TODO move all files to standard file path setup?
                file_path = file_path[:3] + [
                    str(obj.intervention.agreement.partner.pk),
                ] + file_path[3:] + [
                    str(obj.intervention.pk),
                    "amendments",
                    obj_pk
                ]
            else:
                file_path = file_path + [
                    str(obj.intervention.pk),
                    "attachments",
                    obj_pk
                ]
        elif model_name == "intervention":
            file_path = file_path + [
                str(obj.agreement.partner.pk),
                'agreements',
                str(obj.agreement.pk),
                'interventions',
                obj_pk,
                "prc"
            ]
        elif model_name == "agreementamendment":
            file_path = file_path[:-1] + [
                'partner_org',
                str(obj.agreement.partner.pk),
                'agreements',
                obj.agreement.base_number,
                'amendments',
                str(obj.number),
            ]
        else:
            raise Exception("Unknown file path")
    else:
        file_path = [
            "files",
            app,
            slugify(model_name),
            obj_pk,
        ]

    file_path.append(os.path.split(filename)[-1])
    return '/'.join(file_path)


@python_2_unicode_compatible
class Attachment(TimeStampedModel, models.Model):
    file_type = models.ForeignKey(FileType, verbose_name=_('Document Type'))

    file = models.FileField(
        upload_to=generate_file_path,
        blank=True,
        null=True,
        verbose_name=_('File Attachment'),
        max_length=1024
    )
    hyperlink = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Hyperlink'))

    content_type = models.ForeignKey(ContentType)
    object_id = models.IntegerField()
    content_object = GenericForeignKey()

    code = models.CharField(max_length=20, blank=True, verbose_name=_('Code'))

    class Meta:
        ordering = ['id', ]

    def __str__(self):
        return six.text_type(self.file)

    def clean(self):
        super(Attachment, self).clean()
        if bool(self.file) == bool(self.hyperlink):
            raise ValidationError(_('Please provide file or hyperlink.'))

    @property
    def url(self):
        return self.file.url if self.file else self.hyperlink

    @property
    def filename(self):
        return os.path.basename(self.file.name if self.file else urlsplit(self.hyperlink).path)
