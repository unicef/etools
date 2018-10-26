from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.fields import AutoSlugField
from ordered_model.models import OrderedModel


class CheckListCategory(OrderedModel):
    name = models.CharField(max_length=100, verbose_name=_('Name'))

    def __str__(self):
        return self.name


class CheckListItem(OrderedModel):
    question_text = models.CharField(max_length=255, verbose_name=_('Question Text'))
    slug = AutoSlugField(verbose_name=_('Slug'), populate_from='question_text')

    def __str__(self):
        return self.question_text
