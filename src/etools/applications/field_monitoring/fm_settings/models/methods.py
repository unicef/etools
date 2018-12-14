from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.fields import AutoSlugField

from etools.applications.field_monitoring.shared.models import FMMethod


class FMMethodType(models.Model):
    method = models.ForeignKey(FMMethod, verbose_name=_('Method'), related_name='types',
                               on_delete=models.CASCADE)
    name = models.CharField(verbose_name=_('Name'), max_length=300)
    slug = AutoSlugField(verbose_name=_('Slug'), populate_from='name')

    class Meta:
        verbose_name = _('FM Method Type')
        verbose_name_plural = _('FM Method Types')
        ordering = ('id',)

    def __str__(self):
        return self.name
