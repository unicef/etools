from datetime import date

from django.contrib.postgres.fields import JSONField
from django.db import models, transaction
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property

from model_utils.models import TimeStampedModel
from mptt.models import MPTTModel, TreeForeignKey


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


@python_2_unicode_compatible
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

    def __str__(self):
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


@python_2_unicode_compatible
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

    def __str__(self):
        return self.name


@python_2_unicode_compatible
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
    color = models.CharField(max_length=7, null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
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


@python_2_unicode_compatible
class Result(MPTTModel):
    """
    Represents a result, wbs is unique

    Relates to :model:`reports.CountryProgramme`
    Relates to :model:`reports.Sector`
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

    def __str__(self):
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


@python_2_unicode_compatible
class LowerResult(TimeStampedModel):

    # Lower result is always an output

    # link to intermediary model to intervention and cp ouptut
    result_link = models.ForeignKey('partners.InterventionResultLink', related_name='ll_results', null=True)

    name = models.CharField(max_length=500)

    # automatically assigned unless assigned manually in the UI (Lower level WBS - like code)
    code = models.CharField(max_length=50)

    def __str__(self):
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


@python_2_unicode_compatible
class Unit(models.Model):
    """
    Represents an unit of measurement
    """
    type = models.CharField(max_length=45, unique=True)

    class Meta:
        ordering = ['type']

    def __str__(self):
        return self.type


@python_2_unicode_compatible
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

    def __str__(self):
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

    # current total, transactional and dynamically calculated
    total = models.IntegerField(null=True, blank=True, default=0,
                                verbose_name="Current Total")

    # variable disaggregations that may be present in the work plan
    # this can only be present if the indicatorBlueprint has dissagregatable = true
    disaggregation_logic = JSONField(null=True)

    class Meta:
        unique_together = (("indicator", "lower_result"),)


@python_2_unicode_compatible
class Indicator(models.Model):
    """
    Represents an indicator

    Relates to :model:`reports.Unit`
    Relates to :model:`reports.Result`
    """
    # TODO: rename this to RAMIndicator

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

    def __str__(self):
        return u'{}{} {} {}'.format(
            u'' if self.active else u'[Inactive] ',
            self.name,
            u'Baseline: {}'.format(self.baseline) if self.baseline else u'',
            u'Target: {}'.format(self.target) if self.target else u''
        )

    def save(self, *args, **kwargs):
        # Prevent from saving empty strings as code because of the unique together constraint
        if not self.code:
            self.code = None
        super(Indicator, self).save(*args, **kwargs)
