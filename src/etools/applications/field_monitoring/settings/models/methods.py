from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.fields import AutoSlugField

from etools.applications.field_monitoring.shared.models import Method


class MethodType(models.Model):
    method = models.ForeignKey(Method, verbose_name=_('Method'), related_name='types')
    name = models.CharField(verbose_name=_('Name'), max_length=300)
    slug = AutoSlugField(verbose_name=_('Slug'), populate_from='name')

    def __str__(self):
        return self.name

    @staticmethod
    def clean_method(method):
        if not method.is_types_applicable:
            raise ValidationError(_('Unable to add type for this Method'))

    def clean(self):
        super().clean()
        self.clean_method(self.method)
