from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.gis.db.models import PointField
from django.db import models
from django.db.models import QuerySet, Prefetch
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.fields import AutoSlugField
from model_utils import Choices, FieldTracker
from model_utils.models import TimeStampedModel
from ordered_model.models import OrderedModel
from unicef_locations.models import Location

from etools.applications.partners.models import PartnerOrganization
from etools.applications.reports.models import Result, Section


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


class QuestionsQuerySet(QuerySet):
    def prefetch_templates(self, level, target_id=None):
        from etools.applications.field_monitoring.planning.models import QuestionTemplate

        target = Question.get_target_relation_name(level)
        queryset = self.prefetch_related(
            Prefetch('templates', QuestionTemplate.objects.filter(**{'{}__isnull'.format(target): True}),
                     to_attr='base_templates')
        )
        if target_id:
            queryset = queryset.prefetch_related(
                Prefetch(
                    'templates',
                    QuestionTemplate.objects.filter(**{'{}__isnull'.format(target): False, target: target_id}),
                    to_attr='specific_templates'
                )
            )

        return queryset


class Question(models.Model):
    ANSWER_TYPES = Choices(
        ('text', _('Text')),
        ('number', _('Number')),
        ('bool', _('Boolean')),
        ('likert_scale', _('Likert Scale')),
    )

    LEVELS = Choices(
        ('partner', _('Partner')),
        ('output', _('Output')),
        ('intervention', _('PD/SSFA')),
    )

    answer_type = models.CharField(max_length=15, choices=ANSWER_TYPES, verbose_name=_('Answer Type'))
    choices_size = models.PositiveSmallIntegerField(verbose_name=_('Choices Size'), null=True, blank=True)
    level = models.CharField(max_length=15, choices=LEVELS, verbose_name=_('Level'))
    methods = models.ManyToManyField(Method, blank=True, verbose_name=_('Methods'))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name=_('Category'))
    sections = models.ManyToManyField(Section, blank=True, verbose_name=_('Sections'))
    text = models.TextField(verbose_name=_('Question Text'))
    is_hact = models.BooleanField(default=False, verbose_name=_('Count as HACT'))
    is_custom = models.BooleanField(default=False, verbose_name=_('Is Custom'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    objects = models.Manager.from_queryset(QuestionsQuerySet)()

    class Meta:
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')
        ordering = ('id',)

    @classmethod
    def get_target_relation_name(cls, level):
        return {
            cls.LEVELS.partner: 'partner',
            cls.LEVELS.output: 'cp_output',
            cls.LEVELS.intervention: 'intervention',
        }[level]

    @property
    def template(self):
        if hasattr(self, '_template'):
            return self._template

        assert hasattr(self, 'base_templates'), 'Templates should be prefetched firstly'

        if hasattr(self, 'specific_templates') and self.specific_templates:
            return self.specific_templates[0]
        elif self.base_templates:
            return self.base_templates[0]

    @template.setter
    def template(self, value):
        self._template = value

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


class LogIssue(TimeStampedModel):
    STATUS_CHOICES = Choices(
        ('new', 'New'),
        ('past', 'Past'),
    )
    RELATED_TO_TYPE_CHOICES = Choices(
        ('cp_output', _('CP Output')),
        ('partner', _('Partner')),
        ('location', _('Location/Site')),
    )

    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_logissues',
                               verbose_name=_('Issue Raised By'),
                               on_delete=models.CASCADE)
    cp_output = models.ForeignKey(Result, blank=True, null=True, verbose_name=_('CP Output'),
                                  on_delete=models.CASCADE)
    partner = models.ForeignKey(PartnerOrganization, blank=True, null=True, verbose_name=_('Partner'),
                                on_delete=models.CASCADE)
    location = models.ForeignKey(Location, blank=True, null=True, verbose_name=_('Location'),
                                 on_delete=models.CASCADE)
    location_site = models.ForeignKey(LocationSite, blank=True, null=True, verbose_name=_('Site'),
                                      on_delete=models.CASCADE)

    issue = models.TextField(verbose_name=_('Issue For Attention/Probing'))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_CHOICES.new)
    attachments = GenericRelation('unicef_attachments.Attachment', verbose_name=_('Attachments'), blank=True)
    history = GenericRelation('unicef_snapshot.Activity', object_id_field='target_object_id',
                              content_type_field='target_content_type')

    class Meta:
        verbose_name = _('Log Issue')
        verbose_name_plural = _('Log Issues')
        ordering = ('id',)

    def __str__(self):
        return '{}: {}'.format(self.related_to, self.issue)

    @property
    def related_to(self):
        return self.cp_output or self.partner or self.location_site or self.location

    @property
    def related_to_type(self):
        if self.cp_output:
            return self.RELATED_TO_TYPE_CHOICES.cp_output
        elif self.partner:
            return self.RELATED_TO_TYPE_CHOICES.partner
        elif self.location:
            return self.RELATED_TO_TYPE_CHOICES.location
