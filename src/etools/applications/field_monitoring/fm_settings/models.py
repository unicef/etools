from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.fields import AutoSlugField
from model_utils import Choices
from ordered_model.models import OrderedModel

from etools.applications.reports.models import Section


class Method(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=100)

    class Meta:
        verbose_name = _('Method')
        verbose_name_plural = _('Methods')
        ordering = ('id',)

    def __str__(self):
        return self.name


class Category(OrderedModel):
    name = models.CharField(max_length=100, verbose_name=_('Name'))

    class Meta:
        verbose_name = _('Question Category')
        verbose_name_plural = _('Questions Categories')
        ordering = ('order',)

    def __str__(self):
        return self.name


class Question(models.Model):
    ANSWER_TYPES = Choices(
        ('text', _('Text')),
        ('number', _('Number')),
        ('bool', _('Boolean')),
        ('choices', _('Choices')),
    )

    LEVELS = Choices(
        ('partner', _('Partner')),
        ('output', _('Output')),
        ('intervention', _('PD/SSFA')),
    )

    answer_type = models.CharField(max_length=10, choices=ANSWER_TYPES, verbose_name=_('Answer Type'))
    level = models.CharField(max_length=15, choices=LEVELS, verbose_name=_('Level'))
    methods = models.ManyToManyField(Method, blank=True, verbose_name=_('Methods'))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name=_('Category'))
    sections = models.ManyToManyField(Section, blank=True, verbose_name=_('Sections'))
    text = models.TextField(verbose_name=_('Question Text'))
    is_hact = models.BooleanField(default=False, verbose_name=_('Count as HACT'))

    class Meta:
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')
        ordering = ('id',)

    def __str__(self):
        return self.text


class Option(models.Model):
    """
    Possible answers for question in case of choices
    """

    question = models.ForeignKey(Question, related_name='options', verbose_name=_('Question'), on_delete=models.CASCADE)
    label = models.CharField(max_length=50, verbose_name=_('Label'))
    value = AutoSlugField(populate_from='label', verbose_name=_('Value'))

    class Meta:
        verbose_name = _('Option')
        verbose_name_plural = _('Option')
        ordering = ('id',)

    def __str__(self):
        return self.label
