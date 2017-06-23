from datetime import datetime
from django.db import models
from django.contrib.postgres.fields import JSONField

from django.utils.functional import cached_property

from mptt.models import MPTTModel, TreeForeignKey
from paintstore.fields import ColorPickerField

from model_utils.models import TimeStampedModel


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

    def save(self, *args, **kwargs):
        super(Quarter, self).save(*args, **kwargs)


class CountryProgramme(models.Model):
    """
    Represents a country programme cycle
    """
    name = models.CharField(max_length=150)
    wbs = models.CharField(max_length=30, unique=True)
    from_date = models.DateField()
    to_date = models.DateField()

    def __unicode__(self):
        return ' '.join([self.name, self.wbs])

    @classmethod
    def current(cls):
        today = datetime.now()
        cps = cls.objects.filter(wbs__contains='/A0/', from_date__lt=today, to_date__gt=today).order_by('-to_date')
        return cps.first()

    @classmethod
    def encapsulates(cls, date_from, date_to):
        '''
        :param date_from:
        :param date_to:
        :return: CountryProgramme instance - Country programme that contains the dates specified
        raises cls.DoesNotExist if the dates span outside existing country programmes
        raises cls.MultipleObjectsReturned if the dates span multiple country programmes
        '''

        return cls.objects.get(wbs__contains='/A0/', from_date__lte=date_from, to_date__gte=date_to)


class ResultStructure(models.Model):
    """
    Represents a humanitarian response plan in the country programme

    Relates to :model:`reports.CountryProgramme`
    """

    name = models.CharField(max_length=150)
    country_programme = models.ForeignKey(CountryProgramme, null=True, blank=True)
    from_date = models.DateField()
    to_date = models.DateField()
    # TODO: add validation these dates should never extend beyond the country programme structure

    class Meta:
        ordering = ['name']
        unique_together = (("name", "from_date", "to_date"),)

    def __unicode__(self):
        return self.name

    @classmethod
    def current(cls):
        return ResultStructure.objects.order_by('to_date').last()


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
            'country_programme', 'result_structure', 'result_type')


class Result(MPTTModel):
    """
    Represents a result, wbs is unique

    Relates to :model:`reports.CountryProgramme`
    Relates to :model:`reports.ResultStructure`
    Relates to :model:`reports.ResultType`
    """

    result_structure = models.ForeignKey(ResultStructure, null=True, blank=True, on_delete=models.DO_NOTHING)
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
    result_link = models.ForeignKey('partners.InterventionResultLink', related_name='ll_results', null=True)

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
            self.code = '{}-{}'.format(
                self.result_link.intervention.id,
                self.result_link.ll_results.count() + 1
            )
        return super(LowerResult, self).save(**kwargs)


class Goal(models.Model):
    """
    Represents a goal for the humanitarian response plan

    Relates to :model:`reports.ResultStructure`
    Relates to :model:`reports.Sector`
    """

    result_structure = models.ForeignKey(
        ResultStructure, blank=True, null=True, on_delete=models.DO_NOTHING)
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


class IndicatorBlueprint(models.Model):
    NUMBER = u'number'
    PERCENTAGE = u'percentage'
    YESNO = u'yesno'
    UNIT_CHOICES = (
        (NUMBER, NUMBER),
        (PERCENTAGE, PERCENTAGE),
        (YESNO, YESNO)
    )
    name = models.CharField(max_length=1024)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default=NUMBER)
    description = models.CharField(max_length=3072, null=True, blank=True)
    code = models.CharField(max_length=50, null=True, blank=True, unique=True)
    subdomain = models.CharField(max_length=255, null=True, blank=True)
    disaggregatable = models.BooleanField(default=False)

    # TODO: add:
    # siblings (similar inidcators to this indicator)
    # other_representation (exact copies with different names for some random reason)
    # children (indicators that aggregate up to this or contribute to this indicator through a formula)
    # aggregation_types (potential aggregation types: geographic, time-periods ?)
    # calculation_formula (how the children totals add up to this indicator's total value)
    # aggregation_formulas (how the total value is aggregated from the reports if possible)

    def save(self, *args, **kwargs):
        # Prevent from saving empty strings as code because of the unique together constraint
        if self.code == '':
            self.code = None
        super(IndicatorBlueprint, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name


class AppliedIndicator(models.Model):

    indicator = models.ForeignKey(IndicatorBlueprint)

    # the result this indicator is contributing to.
    lower_result = models.ForeignKey(LowerResult, related_name='applied_indicators')

    # unique code for this indicator within the current context
    # eg: (1.1) result code 1 - indicator code 1
    context_code = models.CharField(max_length=50, null=True, blank=True,
                                    verbose_name="Code in current context")
    target = models.CharField(max_length=255, null=True, blank=True)
    baseline = models.CharField(max_length=255, null=True, blank=True)
    assumptions = models.TextField(null=True, blank=True)
    means_of_verification = models.CharField(max_length=255, null=True, blank=True)

    # current total, transactional and dynamically calculated based on IndicatorReports
    total = models.IntegerField(null=True, blank=True, default=0,
                                verbose_name="Current Total")

    # variable disaggregation's that may be present in the work plan
    # this can only be present if the indicatorBlueprint has dissagregatable = true
    disaggregation_logic = JSONField(null=True)

    class Meta:
        unique_together = (("indicator", "lower_result"),)


class Indicator(models.Model):
    """
    Represents an indicator

    Relates to :model:`reports.ResultStructure`
    Relates to :model:`reports.Sector`
    Relates to :model:`reports.Result`
    Relates to :model:`activityinfo.Indicator`
    """
    # TODO: rename this to RAMIndicator and rename/remove RAMIndicator

    sector = models.ForeignKey(
        Sector,
        blank=True, null=True
    )
    result_structure = models.ForeignKey(
        ResultStructure,
        blank=True, null=True, on_delete=models.DO_NOTHING
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

    view_on_dashboard = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']
        unique_together = (("name", "result", "sector"),)

    def __unicode__(self):
        return u'{} {} {}'.format(
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
