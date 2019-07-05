from django.db import models
from django.utils.translation import ugettext_lazy as _


class FMMethod(models.Model):
    # todo: remove
    name = models.CharField(verbose_name=_('Name'), max_length=100)
    is_types_applicable = models.BooleanField(verbose_name=_('Are types allowed?'), default=False)

    class Meta:
        verbose_name = _('FM Method')
        verbose_name_plural = _('FM Methods')
        ordering = ('id',)

    def __str__(self):
        return self.name
