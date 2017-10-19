import os

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible
from django.utils.text import slugify
from django.utils.translation import ugettext as _

from model_utils.models import TimeStampedModel
from ordered_model.models import OrderedModel


@python_2_unicode_compatible
class FileType(OrderedModel, models.Model):
    name = models.CharField(max_length=64)

    code = models.CharField(max_length=64, default="")

    def __str__(self):
        return self.name

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
    file_type = models.ForeignKey(FileType)

    file = models.FileField(upload_to=generate_file_path, blank=True, null=True)
    hyperlink = models.CharField(max_length=255, blank=True, null=True)

    content_type = models.ForeignKey(ContentType)
    object_id = models.IntegerField()
    content_object = GenericForeignKey()

    code = models.CharField(max_length=20, blank=True)

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
