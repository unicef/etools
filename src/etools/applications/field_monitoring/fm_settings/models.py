from django.contrib.gis.db.models import PointField
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.fields import AutoSlugField
from model_utils import FieldTracker, Choices

from model_utils.models import TimeStampedModel
from ordered_model.models import OrderedModel

from unicef_locations.models import Location

from etools.applications.reports.models import Section


class LocationSite(TimeStampedModel):
    parent = models.ForeignKey(
        Location,
        verbose_name=_("Parent Location"),
        related_name='sites',
        db_index=True,
        on_delete=models.CASCADE
    )
    name = models.CharField(verbose_name=_("Name"), max_length=254)
    p_code = models.CharField(
        verbose_name=_("P Code"),
        max_length=32,
        blank=True,
        default='',
    )

    point = PointField(verbose_name=_("Point"), null=True, blank=True)
    is_active = models.BooleanField(verbose_name=_("Active"), default=True, blank=True)

    security_detail = models.TextField(verbose_name=_('Detail on Security'), blank=True)

    tracker = FieldTracker(['point'])

    class Meta:
        verbose_name = _('Location Site')
        verbose_name_plural = _('Location Sites')
        ordering = ('parent', 'id',)

    def __str__(self):
        return u'{}: {}'.format(
            self.name,
            self.p_code if self.p_code else ''
        )

    @staticmethod
    def get_parent_location(point):
        matched_locations = Location.objects.filter(geom__contains=point)
        if not matched_locations:
            location = Location.objects.filter(gateway__admin_level=0).first()
        else:
            leafs = filter(lambda l: l.is_leaf_node(), matched_locations)
            location = min(leafs, key=lambda l: l.geom.length)

        return location

    def save(self, **kwargs):
        if not self.parent_id:
            self.parent = self.get_parent_location(self.point)
            assert self.parent_id, 'Unable to find location for {}'.format(self.point)
        elif self.tracker.has_changed('point'):
            self.parent = self.get_parent_location(self.point)

        super().save(**kwargs)


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
