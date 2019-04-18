import os
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, connection
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import ugettext as _

from model_utils.models import TimeStampedModel
from ordered_model.models import OrderedModel

from unicef_attachments.models import Attachment as NewAttachment


class FileType(OrderedModel, models.Model):
    name = models.CharField(max_length=64, verbose_name=_('Name'))
    label = models.CharField(max_length=64, verbose_name=_('Label'))

    code = models.CharField(max_length=64, default="", verbose_name=_('Code'))

    def __str__(self):
        return self.label

    class Meta:
        unique_together = ("name", "code", )
        ordering = ('code', 'order')


def generate_file_path(attachment, filename):
    # updating other models to use this function,
    # for now maintaining their previous upload
    # paths
    # TODO move all files to standard file path setup?
    if attachment.content_type:
        app = attachment.content_type.app_label
        model_name = attachment.content_type.model
    else:
        app = "unknown"
        model_name = "tmp"
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
            raise ValueError("Unhandled model ({}) in generation of file path".format(
                model_name
            ))
    else:
        file_path = [
            connection.schema_name,
            "files",
            app,
            slugify(model_name),
            attachment.code,
            obj_pk,
        ]

    file_path.append(os.path.split(filename)[-1])
    # strip all '/'
    file_path = [x.strip("/") for x in file_path]
    return '/'.join(file_path)


class Attachment(TimeStampedModel, models.Model):
    file_type = models.ForeignKey(
        FileType,
        verbose_name=_('Document Type'),
        null=True,
        related_name="attachments_old",
        on_delete=models.CASCADE,
    )
    file = models.FileField(
        upload_to=generate_file_path,
        blank=True,
        null=True,
        verbose_name=_('File Attachment'),
        max_length=1024,
    )
    hyperlink = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_('Hyperlink')
    )
    content_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        verbose_name=_('Content Type'),
        related_name="attachments_old",
        on_delete=models.CASCADE,
    )
    object_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_('Object ID')
    )
    content_object = GenericForeignKey()
    code = models.CharField(max_length=64, blank=True, verbose_name=_('Code'))
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Uploaded By"),
        related_name='attachments_old',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ['id', ]

    def __str__(self):
        return str(self.file)

    def clean(self):
        super().clean()
        if bool(self.file) == bool(self.hyperlink):
            raise ValidationError(_('Please provide file or hyperlink.'))

    @property
    def url(self):
        if self.file:
            return self.file.url
        else:
            return self.hyperlink

    @property
    def filename(self):
        return os.path.basename(self.file.name if self.file else urlsplit(self.hyperlink).path)

    @property
    def file_link(self):
        return reverse("attachments:file", args=[self.pk])

    def save(self, *args, **kwargs):
        from etools.applications.attachments.utils import denormalize_attachment

        super().save(*args, **kwargs)
        denormalize_attachment(self)


class AttachmentFlatManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(source="Trips")


class AttachmentFlat(models.Model):
    attachment = models.ForeignKey(
        NewAttachment,
        related_name="denormalized",
        on_delete=models.CASCADE,
    )
    partner = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Partner')
    )
    partner_type = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Partner Type')
    )
    vendor_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Vendor Number')
    )
    pd_ssfa = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('PD SSFA ID')
    )
    pd_ssfa_number = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_('PD SSFA Number')
    )
    agreement_reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Agreement Reference Number')
    )
    object_link = models.URLField(
        blank=True,
        verbose_name=_('Object Link')
    )
    file_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('File Type')
    )
    file_link = models.CharField(
        max_length=1024,
        blank=True,
        verbose_name=_('File Link')
    )
    filename = models.CharField(
        max_length=1024,
        blank=True,
        verbose_name=_('File Name')
    )
    source = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Source'),
    )
    uploaded_by = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Uploaded by')
    )
    created = models.CharField(max_length=50, verbose_name=_('Created'))

    objects = AttachmentFlatManager()

    def __str__(self):
        return str(self.attachment)

    @classmethod
    def get_file_types(cls):
        return cls.objects.exclude(file_type="").values_list(
            "file_type",
            flat=True
        ).distinct("file_type").order_by("file_type")
