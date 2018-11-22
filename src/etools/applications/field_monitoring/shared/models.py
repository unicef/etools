from django.db import models
from django.utils.translation import ugettext_lazy as _


class FMMethod(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=100)
    is_types_applicable = models.BooleanField(verbose_name=_('Are types allowed?'), default=False)

    def __str__(self):
        return self.name
