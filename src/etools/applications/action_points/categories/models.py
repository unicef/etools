from django.db import models
from django.utils.translation import gettext_lazy as _

from model_utils import Choices
from model_utils.models import TimeStampedModel
from ordered_model.models import OrderedModel


class Category(OrderedModel, TimeStampedModel):
    MODULE_CHOICES = Choices(
        ('apd', _('Action Points')),
        ('t2f', _('Trip Management')),
        ('tpm', _('Third Party Monitoring')),
        ('audit', _('Financial Assurance')),
        ('psea', _('PSEA Assessment')),
        ('fm', _('Field Monitoring')),
    )

    module = models.CharField(max_length=10, choices=MODULE_CHOICES, verbose_name=_('Module'))
    description = models.TextField(verbose_name=_('Description'))

    class Meta:
        unique_together = ("description", "module", )
        ordering = ('module', 'order')
        verbose_name = _('Action point category')
        verbose_name_plural = _('Action point categories')

    def __str__(self):
        return '{}: {}'.format(self.module, self.description)
