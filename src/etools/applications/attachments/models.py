
import os

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
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
        return self.label

    class Meta:
        unique_together = ("name", "code", )
        ordering = ('code', 'order')


def generate_file_path(attachment, filename):
    return 'files/{}/{}/{}/{}'.format(
        attachment.content_type.app_label,
        slugify(attachment.content_type.model),
        attachment.object_id,
        os.path.split(filename)[-1]
    )


@python_2_unicode_compatible
class Attachment(TimeStampedModel, models.Model):
    file_type = models.ForeignKey(
        FileType, verbose_name=_('Document Type'),
        on_delete=models.CASCADE,
    )

    file = models.FileField(
        upload_to=generate_file_path,
        blank=True,
        null=True,
        verbose_name=_('File Attachment'),
        max_length=1024,
    )
    hyperlink = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Hyperlink'))

    content_type = models.ForeignKey(
        ContentType, verbose_name=_('Content Type'),
        on_delete=models.CASCADE,
    )
    object_id = models.IntegerField(verbose_name=_('Object ID'))
    content_object = GenericForeignKey()

    code = models.CharField(max_length=64, blank=True, verbose_name=_('Code'))
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Uploaded By"),
        related_name='attachments',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

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

        super(Attachment, self).save(*args, **kwargs)
        denormalize_attachment(self)


@python_2_unicode_compatible
class AttachmentFlat(models.Model):
    attachment = models.ForeignKey(
        Attachment,
        on_delete=models.CASCADE,
    )
    partner = models.CharField(max_length=255, blank=True, verbose_name=_('Partner'))
    partner_type = models.CharField(max_length=150, blank=True, verbose_name=_('Partner Type'))
    vendor_number = models.CharField(max_length=50, blank=True, verbose_name=_('Vendor Number'))
    pd_ssfa_number = models.CharField(max_length=64, blank=True, verbose_name=_('PD SSFA Number'))
    file_type = models.CharField(max_length=100, blank=True, verbose_name=_('File Type'))
    file_link = models.CharField(max_length=1024, blank=True, verbose_name=_('File Link'))
    filename = models.CharField(max_length=1024, blank=True, verbose_name=_('File Name'))
    uploaded_by = models.CharField(max_length=255, blank=True, verbose_name=_('Uploaded by'))
    created = models.CharField(max_length=50, verbose_name=_('Created'))

    def __str__(self):
        return six.text_type(self.attachment)
