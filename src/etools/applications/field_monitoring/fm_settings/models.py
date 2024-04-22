from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.gis.db.models import PointField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Prefetch, QuerySet
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from model_utils import Choices, FieldTracker
from model_utils.models import TimeStampedModel
from ordered_model.models import OrderedModel
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation

from etools.applications.field_monitoring.groups import FMUser
from etools.applications.locations.models import Location
from etools.applications.partners.models import PartnerOrganization
from etools.applications.reports.models import Result, Section


class GlobalConfig(models.Model):
    attachments = CodedGenericRelation(Attachment, verbose_name=_('Global Attachments'), code='fm_global', blank=True)

    class Meta:
        verbose_name = _('Global Config')
        verbose_name_plural = _('Global Configs')
        ordering = ('id',)

    @classmethod
    def get_current(cls):
        # should be only one instance, so just create if missing
        if not hasattr(cls, '_config'):
            cls._config = cls.objects.get_or_create()[0]

        return cls._config

    def get_related_third_party_users(self):
        return get_user_model().objects.filter(realms__group=FMUser.as_group())


class Method(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=100)
    short_name = models.CharField(verbose_name=_('Short Name'), max_length=10)
    use_information_source = models.BooleanField(verbose_name=_('Ask for information source in checklist?'),
                                                 default=False)

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
        ('intervention', _('PD/SPD')),
    )

    answer_type = models.CharField(max_length=15, choices=ANSWER_TYPES, verbose_name=_('Answer Type'))
    choices_size = models.PositiveSmallIntegerField(verbose_name=_('Choices Size'), null=True, blank=True)
    level = models.CharField(max_length=15, choices=LEVELS, verbose_name=_('Level'))
    methods = models.ManyToManyField(Method, verbose_name=_('Methods'))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name=_('Category'))
    sections = models.ManyToManyField(Section, verbose_name=_('Sections'), blank=True)
    text = models.TextField(verbose_name=_('Question Text'))
    is_hact = models.BooleanField(default=False, verbose_name=_('Count as HACT'))
    is_custom = models.BooleanField(default=False, verbose_name=_('Is Custom'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    order = models.PositiveIntegerField(db_index=True, default=1)

    objects = models.Manager.from_queryset(QuestionsQuerySet)()

    class Meta:
        verbose_name = _('Question')
        verbose_name_plural = _('Questions')
        ordering = ('order',)

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
    label = models.CharField(max_length=100, verbose_name=_('Label'))
    # TODO: remove json field usage and replace with Charfield as this is only used without a structure:
    # eg: value = 1, value = "Characters", value = True -> used only for automatic typecasting and cand be confusing
    value = models.JSONField(verbose_name=_('Value'), blank=True, null=True)

    class Meta:
        verbose_name = _('Option')
        verbose_name_plural = _('Option')
        ordering = ('id',)
        unique_together = ('question', 'value')

    def __str__(self):
        return self.label

    def save(self, **kwargs):
        if self.value is None:
            self.value = slugify(self.label)
        super().save(**kwargs)


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
        return u'{}{}'.format(
            self.name,
            f': {self.p_code}' if self.p_code else ''
        )

    @staticmethod
    def get_parent_location(point):
        locations = Location.objects.all_with_geom().filter(geom__contains=point, is_active=True)
        if locations:
            matched_locations = list(filter(lambda l: l.is_leaf_node(), locations)) or locations
            location = min(matched_locations, key=lambda l: l.geom.length)
        else:
            location = Location.objects.filter(admin_level=0, is_active=True).first()

        return location

    def save(self, **kwargs):
        if not self.parent_id:
            self.parent = self.get_parent_location(self.point)
            assert self.parent_id, 'Unable to find location for {}'.format(self.point)
        elif self.tracker.has_changed('point') and self.pk:
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
                                  on_delete=models.CASCADE, related_name='log_issues')
    partner = models.ForeignKey(PartnerOrganization, blank=True, null=True, verbose_name=_('Partner'),
                                on_delete=models.CASCADE, related_name='log_issues')
    location = models.ForeignKey(Location, blank=True, null=True, verbose_name=_('Location'),
                                 on_delete=models.CASCADE, related_name='log_issues')
    location_site = models.ForeignKey(LocationSite, blank=True, null=True, verbose_name=_('Site'),
                                      on_delete=models.CASCADE, related_name='log_issues')

    issue = models.TextField(verbose_name=_('Issue For Attention/Probing'))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_CHOICES.new)
    attachments = CodedGenericRelation('unicef_attachments.Attachment', code='attachments',
                                       verbose_name=_('Attachments'), blank=True)
    history = GenericRelation('unicef_snapshot.Activity', object_id_field='target_object_id',
                              content_type_field='target_content_type')

    class Meta:
        verbose_name = _('Log Issue')
        verbose_name_plural = _('Log Issues')
        ordering = ('id',)

    def __str__(self):
        return '{}: {}'.format(self.related_to, self.issue)

    @staticmethod
    def _validate_related_objects(cp_output, partner, location):
        provided_values = [v for v in [cp_output, partner, location] if v]

        if not provided_values:
            raise ValidationError(_('Related object not provided'))

        if len(provided_values) != 1:
            raise ValidationError(_('Maximum one related object should be provided'))

    def save(self, **kwargs):
        self._validate_related_objects(self.cp_output, self.partner, self.location)
        super().save(**kwargs)

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

    def get_related_third_party_users(self):
        return get_user_model().objects.filter(realms__group=FMUser.as_group())
