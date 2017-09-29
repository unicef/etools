from __future__ import unicode_literals
from datetime import date

from django.db import models, transaction
from django.utils.functional import cached_property
from django.utils.six import python_2_unicode_compatible
from model_utils.models import TimeStampedModel
from mptt.models import MPTTModel, TreeForeignKey
from paintstore.fields import ColorPickerField

from locations.models import Location
from users.models import Section


class Quarter(models.Model):

    Q1 = 'Q1'
    Q2 = 'Q2'
    Q3 = 'Q3'
    Q4 = 'Q4'

    QUARTER_CHOICES = (
        (Q1, 'Quarter 1'),
        (Q2, 'Quarter 2'),
        (Q3, 'Quarter 3'),
        (Q4, 'Quarter 4'),
    )

    name = models.CharField(max_length=64, choices=QUARTER_CHOICES)
    year = models.CharField(max_length=4)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __repr__(self):
        return '{}-{}'.format(self.name, self.year)


class CountryProgrammeManager(models.Manager):
    def get_queryset(self):
        return super(CountryProgrammeManager, self).get_queryset().filter(invalid=False)

    @property
    def all_active_and_future(self):
        today = date.today()
        return self.get_queryset().filter(to_date__gt=today)

    @property
    def all_future(self):
        today = date.today()
        return self.get_queryset().filter(from_date__gt=today)

    @property
    def all_active(self):
        today = date.today()
        return self.get_queryset().filter(from_date__lte=today, to_date__gt=today)


class CountryProgramme(models.Model):
    """
    Represents a country programme cycle
    """
    name = models.CharField(max_length=150)
    wbs = models.CharField(max_length=30, unique=True)
    invalid = models.BooleanField(default=False)
    from_date = models.DateField()
    to_date = models.DateField()

    objects = CountryProgrammeManager()

    def __unicode__(self):
        return ' '.join([self.name, self.wbs])

    @cached_property
    def active(self):
        today = date.today()
        return self.from_date <= today < self.to_date

    @cached_property
    def future(self):
        today = date.today()
        return self.from_date >= today

    @cached_property
    def expired(self):
        today = date.today()
        return self.to_date < today

    @cached_property
    def special(self):
        return self.wbs[5] != 'A'

    @classmethod
    def main_active(cls):
        today = date.today()
        cps = cls.objects.filter(wbs__contains='/A0/', from_date__lt=today, to_date__gt=today).order_by('-to_date')
        return cps.first()

    def save(self, *args, **kwargs):
        if 'A0/99' in self.wbs:
            self.invalid = True

        if self.pk:
            old_version = CountryProgramme.objects.get(id=self.pk)
            if old_version.to_date != self.to_date:
                from partners.models import Agreement
                with transaction.atomic():
                    Agreement.objects.filter(agreement_type='PCA', country_programme=self).update(end=self.to_date)
                    super(CountryProgramme, self).save(*args, **kwargs)
                    return
        super(CountryProgramme, self).save(*args, **kwargs)


class ResultType(models.Model):
    """
    Represents a result type
    """

    OUTCOME = 'Outcome'
    OUTPUT = 'Output'
    ACTIVITY = 'Activity'

    NAME_CHOICES = (
        (OUTCOME, 'Outcome'),
        (OUTPUT, 'Output'),
        (ACTIVITY, 'Activity'),
    )
    name = models.CharField(max_length=150, unique=True, choices=NAME_CHOICES)

    def __unicode__(self):
        return self.name


class Sector(models.Model):
    """
    Represents a sector
    """

    name = models.CharField(max_length=45, unique=True)
    description = models.CharField(
        max_length=256,
        blank=True,
        null=True
    )
    alternate_id = models.IntegerField(
        blank=True,
        null=True
    )
    alternate_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    dashboard = models.BooleanField(
        default=False
    )
    color = ColorPickerField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return u'{} {}'.format(
            self.alternate_id if self.alternate_id else '',
            self.name
        )


class ResultManager(models.Manager):
    def get_queryset(self):
        return super(ResultManager, self).get_queryset().select_related(
            'country_programme', 'result_type')


class OutputManager(models.Manager):
    def get_queryset(self):
        return super(OutputManager, self).get_queryset().filter(result_type__name=ResultType.OUTPUT).select_related(
            'country_programme', 'result_type')


class Result(MPTTModel):
    """
    Represents a result, wbs is unique

    Relates to :model:`reports.CountryProgramme`
    Relates to :model:`reports.ResultStructure`
    Relates to :model:`reports.ResultType`
    """
    country_programme = models.ForeignKey(CountryProgramme, null=True, blank=True)
    result_type = models.ForeignKey(ResultType)
    sector = models.ForeignKey(Sector, null=True, blank=True)
    name = models.TextField()
    code = models.CharField(max_length=50, null=True, blank=True)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    parent = TreeForeignKey(
        'self',
        null=True, blank=True,
        related_name='children',
        db_index=True
    )

    # activity level attributes
    humanitarian_tag = models.BooleanField(default=False)
    wbs = models.CharField(max_length=50, null=True, blank=True)
    vision_id = models.CharField(max_length=10, null=True, blank=True)
    gic_code = models.CharField(max_length=8, null=True, blank=True)
    gic_name = models.CharField(max_length=255, null=True, blank=True)
    sic_code = models.CharField(max_length=8, null=True, blank=True)
    sic_name = models.CharField(max_length=255, null=True, blank=True)
    activity_focus_code = models.CharField(max_length=8, null=True, blank=True)
    activity_focus_name = models.CharField(max_length=255, null=True, blank=True)

    hidden = models.BooleanField(default=False)
    ram = models.BooleanField(default=False)

    objects = ResultManager()
    outputs = OutputManager()

    class Meta:
        ordering = ['name']
        unique_together = (('wbs', 'country_programme'),)

    @cached_property
    def result_name(self):
        return u'{} {}: {}'.format(
            self.code if self.code else u'',
            self.result_type.name,
            self.name
        )

    @cached_property
    def output_name(self):
        assert self.result_type.name == ResultType.OUTPUT

        return u'{}{}{}'.format(
            '[Expired] ' if self.expired else '',
            'Special- ' if self.special else '',
            self.name
        )

    @cached_property
    def expired(self):
        today = date.today()
        return self.to_date < today

    @cached_property
    def special(self):
        return self.country_programme.special

    def __unicode__(self):
        return u'{} {}: {}'.format(
            self.code if self.code else u'',
            self.result_type.name,
            self.name
        )

    def valid_entry(self):
        if self.wbs:
            return self.wbs.startswith(self.country_programme.wbs)

    def save(self, *args, **kwargs):
        # TODO add a validator that makes sure that the current result wbs fits within the countryProgramme wbs
        if not self.wbs:
            self.wbs = None
        super(Result, self).save(*args, **kwargs)
        nodes = self.get_descendants()
        for node in nodes:
            if node.hidden is not self.hidden:
                node.hidden = self.hidden
                node.save()


class LowerResult(TimeStampedModel):

    # Lower result is always an output

    # link to intermediary model to intervention and cp ouptut
    result_link = models.ForeignKey('partners.InterventionResultLink', related_name='ll_results')

    name = models.CharField(max_length=500)

    # automatically assigned unless assigned manually in the UI (Lower level WBS - like code)
    code = models.CharField(max_length=50)

    def __unicode__(self):
        return u'{}: {}'.format(
            self.code,
            self.name
        )

    class Meta:
        unique_together = (('result_link', 'code'),)
        ordering = ('-created',)

    def save(self, **kwargs):
        if not self.code:
            try:
                latest_ll_id = self.result_link.ll_results.latest('id').id
            except LowerResult.DoesNotExist:
                latest_ll_id = 0

            self.code = '{}-{}'.format(
                self.result_link.intervention.id,
                latest_ll_id + 1
            )
        return super(LowerResult, self).save(**kwargs)


class Goal(models.Model):
    """
    Represents a goal for the humanitarian response plan

    Relates to :model:`reports.ResultStructure`
    Relates to :model:`reports.Sector`
    """
    sector = models.ForeignKey(Sector, related_name='goals')
    name = models.CharField(max_length=512, unique=True)
    description = models.CharField(max_length=512, blank=True)

    class Meta:
        verbose_name = 'CCC'
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Unit(models.Model):
    """
    Represents an unit of measurement
    """
    type = models.CharField(max_length=45, unique=True)

    class Meta:
        ordering = ['type']

    def __unicode__(self):
        return self.type


class IndicatorBlueprint(TimeStampedModel):
    """
    IndicatorBlueprint module is a pattern for indicator
    (here we setup basic parameter).
    """
    NUMBER = 'number'
    PERCENTAGE = 'percentage'
    LIKERT = 'likert'
    YESNO = 'yesno'
    UNIT_CHOICES = (
        (NUMBER, NUMBER),
        (PERCENTAGE, PERCENTAGE),
        # (LIKERT, LIKERT),
        # (YESNO, YESNO),
    )

    SUM = 'sum'
    MAX = 'max'
    AVG = 'avg'
    RATIO = 'ratio'

    QUANTITY_CALC_CHOICES = (
        (SUM, SUM),
        (MAX, MAX),
        (AVG, AVG)
    )

    RATIO_CALC_CHOICES = (
        (PERCENTAGE, PERCENTAGE),
        (RATIO, RATIO)
    )

    CALC_CHOICES = QUANTITY_CALC_CHOICES + RATIO_CALC_CHOICES

    QUANTITY_DISPLAY_TYPE_CHOICES = (
        (NUMBER, NUMBER),
    )

    RATIO_DISPLAY_TYPE_CHOICES = (
        (PERCENTAGE, PERCENTAGE),
        (RATIO, RATIO)
    )

    DISPLAY_TYPE_CHOICES = QUANTITY_DISPLAY_TYPE_CHOICES + RATIO_DISPLAY_TYPE_CHOICES

    title = models.CharField(max_length=1024)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default=NUMBER)
    description = models.CharField(max_length=3072, null=True, blank=True)
    code = models.CharField(max_length=50, null=True, blank=True, unique=True)
    subdomain = models.CharField(max_length=255, null=True, blank=True)
    disaggregatable = models.BooleanField(default=False)

    calculation_formula_across_periods = models.CharField(max_length=10, choices=CALC_CHOICES, default=SUM)
    calculation_formula_across_locations = models.CharField(max_length=10, choices=CALC_CHOICES, default=SUM)

    display_type = models.CharField(max_length=10, choices=DISPLAY_TYPE_CHOICES, default=NUMBER)

    def save(self, *args, **kwargs):
        # Prevent from saving empty strings as code because of the unique together constraint
        if self.code == '':
            self.code = None
        super(IndicatorBlueprint, self).save(*args, **kwargs)

    class Meta:
        ordering = ['-id']


@python_2_unicode_compatible
class Disaggregation(TimeStampedModel):
    """
    Disaggregation model. For example: <Gender, Age>

    As an example, the Disaggregation could be <Age>, and it would have multiple "categories"
    such as: <1, 1-5, 5-18, 18-64, 65+. Each of those categories would be a DisaggregationValue.
    """
    name = models.CharField(max_length=255, unique=True)
    active = models.BooleanField(default=False)

    def __str__(self):
        return "Disaggregation <pk:%s>" % self.id


@python_2_unicode_compatible
class DisaggregationValue(TimeStampedModel):
    """
    Disaggregation Value model. For example: Gender <Male, Female, Other>

    related models:
        Disaggregation (ForeignKey): "disaggregation"
    """
    disaggregation = models.ForeignKey(Disaggregation, related_name="disaggregation_values")
    value = models.CharField(max_length=15)
    active = models.BooleanField(default=False)

    def __str__(self):
        return "Disaggregation Value <pk:%s>" % self.id


class AppliedIndicator(TimeStampedModel):
    """
       Applied Indicator: a contextualized Indicator (an indicator with a target,
           targeted in specific locations, connected to a PD, etc)

       related models:
           reports.Disaggregation (ManyToMany): "disaggregation"
           locations.Location (ManyToMany): "locations"

       """

    indicator = models.ForeignKey(IndicatorBlueprint, null=True, blank=True)

    section = models.ForeignKey(Section, null=True, blank=True)

    cluster_indicator_id = models.PositiveIntegerField(blank=True, null=True)
    cluster_indicator_title = models.CharField(max_length=1024, blank=True, null=True)

    # the result this indicator is contributing to.
    lower_result = models.ForeignKey(LowerResult, related_name='applied_indicators')

    # unique code for this indicator within the current context
    # eg: (1.1) result code 1 - indicator code 1
    context_code = models.CharField(max_length=50, null=True, blank=True,
                                    verbose_name="Code in current context")

    target = models.PositiveIntegerField(default=0)

    baseline = models.PositiveIntegerField(null=True, blank=True)

    assumptions = models.TextField(null=True, blank=True)
    means_of_verification = models.CharField(max_length=255, null=True, blank=True)

    # current total, # not stored or calculated for now
    total = models.IntegerField(null=True, blank=True, default=0,
                                verbose_name="Current Total")

    disaggregation = models.ManyToManyField(Disaggregation, related_name='applied_indicators', blank=True)

    locations = models.ManyToManyField(Location, related_name='applied_indicators')

    class Meta:
        unique_together = (("indicator", "lower_result"),)


class Indicator(models.Model):
    """
    Represents an indicator

    Relates to :model:`reports.ResultStructure`
    Relates to :model:`reports.Sector`
    Relates to :model:`reports.Result`
    """
    # TODO: rename this to RAMIndicator and rename/remove RAMIndicator

    sector = models.ForeignKey(
        Sector,
        blank=True, null=True
    )

    result = models.ForeignKey(Result, null=True, blank=True)
    name = models.CharField(max_length=1024)
    code = models.CharField(max_length=50, null=True, blank=True)
    unit = models.ForeignKey(Unit, null=True, blank=True)

    total = models.IntegerField(verbose_name='UNICEF Target', null=True, blank=True)
    sector_total = models.IntegerField(verbose_name='Sector Target', null=True, blank=True)
    current = models.IntegerField(null=True, blank=True, default=0)
    sector_current = models.IntegerField(null=True, blank=True)
    assumptions = models.TextField(null=True, blank=True)

    # RAM Info
    target = models.CharField(max_length=255, null=True, blank=True)
    baseline = models.CharField(max_length=255, null=True, blank=True)
    ram_indicator = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    view_on_dashboard = models.BooleanField(default=False)

    class Meta:
        ordering = ['-active', 'name']  # active indicators will show up first in the list
        unique_together = (("name", "result", "sector"),)

    def __unicode__(self):
        return u'{}{} {} {}'.format(
            u'' if self.active else u'[Inactive] ',
            self.name,
            u'Baseline: {}'.format(self.baseline) if self.baseline else u'',
            u'Target: {}'.format(self.target) if self.target else u''
        )

    def programmed_amounts(self):
        from partners.models import PCA
        return self.resultchain_set.filter(
            partnership__status__in=[PCA.ACTIVE, PCA.IMPLEMENTED]
        )

    def programmed(self, result_structure=None):
        programmed = self.programmed_amounts()
        if result_structure:
            programmed = programmed.filter(
                partnership__result_structure=result_structure,

            )
        total = programmed.aggregate(models.Sum('target'))
        return total[total.keys()[0]] or 0

    def progress(self, result_structure=None):
        programmed = self.programmed_amounts()
        if result_structure:
            programmed = programmed.filter(
                partnership__result_structure=result_structure,

            )
        total = programmed.aggregate(models.Sum('current_progress'))
        return (total[total.keys()[0]] or 0) + self.current if self.current else 0

    def save(self, *args, **kwargs):
        # Prevent from saving empty strings as code because of the unique together constraint
        if not self.code:
            self.code = None
        super(Indicator, self).save(*args, **kwargs)
