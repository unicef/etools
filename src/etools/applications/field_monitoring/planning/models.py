from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.gis.db.models import PointField
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices, FieldTracker
from model_utils.models import TimeStampedModel
from unicef_locations.models import Location

from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.reports.models import Result


class YearPlan(TimeStampedModel):
    year = models.PositiveSmallIntegerField(primary_key=True)

    prioritization_criteria = models.TextField(verbose_name=_('Prioritization Criteria'), blank=True)
    methodology_notes = models.TextField(verbose_name=_('Methodology Notes & Standards'), blank=True)
    target_visits = models.PositiveSmallIntegerField(verbose_name=_('Target Visits For The Year'),
                                                     blank=True, default=0)
    modalities = models.TextField(verbose_name=_('Modalities'), blank=True)
    partner_engagement = models.TextField(verbose_name=_('Partner Engagement'), blank=True)
    other_aspects = models.TextField(verbose_name=_('Other Aspects of the Field Monitoring Plan'), blank=True)
    history = GenericRelation('unicef_snapshot.Activity', object_id_field='target_object_id',
                              content_type_field='target_content_type')

    class Meta:
        verbose_name = _('Year Plan')
        verbose_name_plural = _('Year Plans')
        ordering = ('year',)

    @classmethod
    def get_defaults(cls, year):
        previous_year_plan = cls._default_manager.filter(year=int(year) - 1).first()
        if not previous_year_plan:
            return {}

        return {
            field: getattr(previous_year_plan, field) for field in
            ['prioritization_criteria', 'methodology_notes', 'target_visits', 'modalities', 'partner_engagement']
            if getattr(previous_year_plan, field)
        }

    def __str__(self):
        return 'Year Plan for {}'.format(self.year)


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


class QuestionTargetMixin(models.Model):
    partner = models.ForeignKey(PartnerOrganization, blank=True, null=True, verbose_name=_('Partner'),
                                on_delete=models.CASCADE)
    cp_output = models.ForeignKey(Result, blank=True, null=True, verbose_name=_('Partner'),
                                  on_delete=models.CASCADE)
    intervention = models.ForeignKey(Intervention, blank=True, null=True, verbose_name=_('Partner'),
                                     on_delete=models.CASCADE)

    @property
    def related_to(self):
        return self.partner or self.cp_output or self.intervention

    class Meta:
        abstract = True


class QuestionTemplate(QuestionTargetMixin, models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name=_('Question'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    specific_details = models.TextField(verbose_name=_('Specific Details To Probe'), blank=True)

    class Meta:
        verbose_name = _('Question Template')
        verbose_name_plural = _('Question Templates')
        ordering = ('id',)

    def __str__(self):
        return 'Question Template for {}'.format(self.related_to)
