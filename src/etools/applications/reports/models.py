# -*- coding: utf-8 -*-
from datetime import date

from django.contrib.postgres.fields import JSONField
from django.db import models, transaction
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _

from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from model_utils.models import TimeStampedModel
from mptt.models import MPTTModel, TreeForeignKey

from etools.applications.locations.models import Location


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

    name = models.CharField(max_length=64, choices=QUARTER_CHOICES, verbose_name=_('Name'))
    year = models.CharField(max_length=4, verbose_name=_('Year'))
    start_date = models.DateTimeField(verbose_name=_('Start Date'))
    end_date = models.DateTimeField(verbose_name=_('End Date'))

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
    name = models.CharField(max_length=150, verbose_name=_('Name'))
    wbs = models.CharField(max_length=30, unique=True, verbose_name=_('WBS'))
    invalid = models.BooleanField(default=False, verbose_name=_('Invalid'))
    from_date = models.DateField(verbose_name=_('From Date'))
    to_date = models.DateField(verbose_name=_('To Date'))

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
                from etools.applications.partners.models import Agreement
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
    name = models.CharField(max_length=150, unique=True, choices=NAME_CHOICES, verbose_name=_('Name'))

    def __str__(self):
        return self.name


class Sector(TimeStampedModel):
    """
    Represents a sector
    """

    name = models.CharField(max_length=45, unique=True, verbose_name=_('Name'))
    description = models.CharField(max_length=256, blank=True, null=True, verbose_name=_('Description'))
    alternate_id = models.IntegerField(blank=True, null=True, verbose_name=_('Alternate ID'))
    alternate_name = models.CharField(max_length=255, null=True, default='', verbose_name=_('Alternate Name'))
    dashboard = models.BooleanField(default=False, verbose_name=_('Dashboard'))
    color = models.CharField(max_length=7, null=True, blank=True, verbose_name=_('Color'))

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


class Result(MPTTModel):
    """
    Represents a result, wbs is unique

    Relates to :model:`reports.CountryProgramme`
    Relates to :model:`reports.Sector`
    Relates to :model:`reports.ResultType`
    """
    country_programme = models.ForeignKey(
        CountryProgramme,
        verbose_name=_("Country Programme"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    result_type = models.ForeignKey(
        ResultType, verbose_name=_("Result Type"),
        on_delete=models.CASCADE,
    )
    sector = models.ForeignKey(
        Sector,
        verbose_name=_("Section"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    name = models.TextField(verbose_name=_("Name"))
    code = models.CharField(
        verbose_name=_("Code"),
        max_length=50,
        null=True,
        blank=True,
    )
    from_date = models.DateField(
        verbose_name=_("From Date"),
        null=True,
        blank=True,
    )
    to_date = models.DateField(
        verbose_name=_("To Date"),
        null=True,
        blank=True,
    )
    parent = TreeForeignKey(
        'self',
        verbose_name=_("Parent"),
        null=True,
        blank=True,
        related_name='children',
        db_index=True,
        on_delete=models.CASCADE,
    )

    # activity level attributes
    humanitarian_tag = models.BooleanField(
        verbose_name=_("Humanitarian Tag"),
        default=False,
    )
    # This must be nullable so it can be optional without breaking
    # uniqueness
    wbs = models.CharField(
        verbose_name=_("WBS"),
        max_length=50,
        null=True,
        blank=True,
    )
    vision_id = models.CharField(
        verbose_name=_("VISION ID"),
        max_length=10,
        null=True,
        blank=True,
    )
    gic_code = models.CharField(
        verbose_name=_("GIC Code"),
        max_length=8,
        null=True,
        blank=True,
    )
    gic_name = models.CharField(
        verbose_name=_("GIC Name"),
        max_length=255,
        null=True,
        blank=True,
    )
    sic_code = models.CharField(
        verbose_name=_("SIC Code"),
        max_length=8,
        null=True,
        blank=True,
    )
    sic_name = models.CharField(
        verbose_name=_("SIC Name"),
        max_length=255,
        null=True,
        blank=True,
    )
    activity_focus_code = models.CharField(
        verbose_name=_("Activity Focus Code"),
        max_length=8,
        null=True,
        blank=True,
    )
    activity_focus_name = models.CharField(
        verbose_name=_("Activity Focus Code"),
        max_length=255,
        null=True,
        blank=True,
    )

    hidden = models.BooleanField(verbose_name=_("Hidden"), default=False)
    ram = models.BooleanField(verbose_name=_("RAM"), default=False)
    created = AutoCreatedField(_('created'))
    modified = AutoLastModifiedField(_('modified'))

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


class LowerResult(TimeStampedModel):

    # Lower result is always an output

    # link to intermediary model to intervention and cp ouptut
    result_link = models.ForeignKey(
        'partners.InterventionResultLink',
        related_name='ll_results',
        verbose_name=_('Result Link'),
        on_delete=models.CASCADE,
    )

    name = models.CharField(verbose_name=_("Name"), max_length=500)

    # automatically assigned unless assigned manually in the UI (Lower level WBS - like code)
    code = models.CharField(verbose_name=_("Code"), max_length=50)

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
            try:
                latest_ll_id = self.result_link.ll_results.latest('id').id
            except LowerResult.DoesNotExist:
                latest_ll_id = 0

            self.code = '{}-{}'.format(
                self.result_link.intervention.id,
                latest_ll_id + 1
            )
        super(LowerResult, self).save(**kwargs)

        # reset certain caches
        self.result_link.intervention.clear_caches()


class Unit(models.Model):
    """
    Represents an unit of measurement
    """
    type = models.CharField(max_length=45, unique=True, verbose_name=_('Type'))

    class Meta:
        ordering = ['type']

    def __str__(self):
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

    title = models.CharField(verbose_name=_("Title"), max_length=1024)
    unit = models.CharField(
        verbose_name=_("Unit"),
        max_length=10,
        choices=UNIT_CHOICES,
        default=NUMBER,
    )
    description = models.CharField(
        verbose_name=_("Description"),
        max_length=3072,
        null=True,
        blank=True,
    )
    code = models.CharField(
        verbose_name=_("Code"),
        max_length=50,
        null=True,
        blank=True,
        unique=True,
    )
    subdomain = models.CharField(
        verbose_name=_("Subdomain"),
        max_length=255,
        null=True,
        blank=True,
    )
    disaggregatable = models.BooleanField(
        verbose_name=_("Disaggregatable"),
        default=False,
    )
    calculation_formula_across_periods = models.CharField(
        verbose_name=_("Calculation Formula across Periods"),
        max_length=10,
        choices=CALC_CHOICES,
        default=SUM,
    )
    calculation_formula_across_locations = models.CharField(
        verbose_name=_("Calculation Formula across Locations"),
        max_length=10,
        choices=CALC_CHOICES,
        default=SUM,
    )
    display_type = models.CharField(
        verbose_name=_("Display Type"),
        max_length=10,
        choices=DISPLAY_TYPE_CHOICES,
        default=NUMBER,
    )

    def save(self, *args, **kwargs):
        # Prevent from saving empty strings as code because of the unique together constraint
        if self.code == '':
            self.code = None
        super(IndicatorBlueprint, self).save(*args, **kwargs)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.title


class Disaggregation(TimeStampedModel):
    """
    Disaggregation model. For example: <Gender, Age>

    As an example, the Disaggregation could be <Age>, and it would have multiple "categories"
    such as: <1, 1-5, 5-18, 18-64, 65+. Each of those categories would be a DisaggregationValue.
    """
    name = models.CharField(max_length=255, unique=True, verbose_name=_('Name'))
    active = models.BooleanField(default=False, verbose_name=_('Active'))

    def __str__(self):
        return self.name


class DisaggregationValue(TimeStampedModel):
    """
    Disaggregation Value model. For example: Gender <Male, Female, Other>

    related models:
        Disaggregation (ForeignKey): "disaggregation"
    """
    disaggregation = models.ForeignKey(
        Disaggregation, related_name="disaggregation_values",
        verbose_name=_('Disaggregation'),
        on_delete=models.CASCADE,
    )
    value = models.CharField(max_length=15, verbose_name=_('Value'))
    active = models.BooleanField(default=False, verbose_name=_('Active'))

    def __str__(self):
        return "Disaggregation Value {} -> {}".format(self.disaggregation, self.value)


class AppliedIndicator(TimeStampedModel):
    """
       Applied Indicator: a contextualized Indicator (an indicator with a target,
           targeted in specific locations, connected to a PD, etc)

       related models:
           reports.Disaggregation (ManyToMany): "disaggregation"
           locations.Location (ManyToMany): "locations"

       """

    indicator = models.ForeignKey(
        IndicatorBlueprint,
        verbose_name=_("Indicator"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    measurement_specifications = models.TextField(max_length=4048, blank=True, null=True)
    label = models.TextField(max_length=4048, blank=True, null=True)
    numerator_label = models.CharField(max_length=256, blank=True, null=True)
    denominator_label = models.CharField(max_length=256, blank=True, null=True)

    section = models.ForeignKey(
        Sector,
        verbose_name=_("Section"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    cluster_indicator_id = models.PositiveIntegerField(
        verbose_name=_("Cluster Indicator ID"),
        blank=True,
        null=True,
    )
    response_plan_name = models.CharField(
        verbose_name=_("Response plan name"),
        max_length=1024,
        blank=True,
        null=True,
    )
    cluster_name = models.CharField(
        verbose_name=_("Cluster Name"),
        max_length=512,
        blank=True,
        null=True,
    )
    cluster_indicator_title = models.CharField(
        verbose_name=_("Cluster Indicator Title"),
        max_length=1024,
        blank=True,
        null=True,
    )

    # the result this indicator is contributing to.
    lower_result = models.ForeignKey(
        LowerResult,
        verbose_name=_("PD Result"),
        related_name='applied_indicators',
        on_delete=models.CASCADE,
    )

    # unique code for this indicator within the current context
    # eg: (1.1) result code 1 - indicator code 1
    context_code = models.CharField(
        verbose_name=_("Code in current context"),
        max_length=50,
        null=True,
        blank=True,
    )
    target = models.PositiveIntegerField(verbose_name=_("Target"), default=0)
    baseline = models.PositiveIntegerField(
        verbose_name=_("Baseline"),
        null=True,
        blank=True,
    )
    target_new = JSONField(default=dict([('d', 1), ('v', 0)]))
    baseline_new = JSONField(default=dict([('d', 1), ('v', 0)]))

    assumptions = models.TextField(
        verbose_name=_("Assumptions"),
        null=True,
        blank=True,
    )
    means_of_verification = models.CharField(
        verbose_name=_("Means of Verification"),
        max_length=255,
        null=True,
        blank=True,
    )

    # current total, transactional and dynamically calculated based on IndicatorReports
    total = models.IntegerField(
        verbose_name=_("Current Total"),
        null=True,
        blank=True,
        default=0,
    )

    # variable disaggregation's that may be present in the work plan
    # this can only be present if the indicatorBlueprint has dissagregatable = true
    disaggregation = models.ManyToManyField(
        Disaggregation,
        verbose_name=_("Disaggregation Logic"),
        related_name='applied_indicators',
        blank=True,
    )
    locations = models.ManyToManyField(
        Location,
        verbose_name=_("Location"),
        related_name='applied_indicators',
    )
    is_high_frequency = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = (("indicator", "lower_result"),)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # reset certain caches
        self.lower_result.result_link.intervention.clear_caches()


class Indicator(TimeStampedModel):
    """
    Represents an indicator

    Relates to :model:`reports.Unit`
    Relates to :model:`reports.Result`
    """
    # TODO: rename this to RAMIndicator

    sector = models.ForeignKey(
        Sector,
        verbose_name=_("Section"),
        blank=True, null=True,
        on_delete=models.CASCADE,
    )

    result = models.ForeignKey(
        Result,
        verbose_name=_("Result"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    name = models.CharField(verbose_name=_("Name"), max_length=1024)
    code = models.CharField(
        verbose_name=_("Code"),
        max_length=50,
        null=True,
        blank=True,
    )
    unit = models.ForeignKey(
        Unit,
        verbose_name=_("Unit"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    total = models.IntegerField(
        verbose_name=_('UNICEF Target'),
        null=True,
        blank=True,
    )
    sector_total = models.IntegerField(
        verbose_name=_('Sector Target'),
        null=True,
        blank=True,
    )
    current = models.IntegerField(
        verbose_name=_("Current"),
        null=True,
        blank=True,
        default=0,
    )
    sector_current = models.IntegerField(
        verbose_name=_("Sector Current"),
        null=True,
        blank=True,
    )
    assumptions = models.TextField(
        verbose_name=_("Assumptions"),
        null=True,
        blank=True,
    )

    # RAM Info
    target = models.CharField(
        verbose_name=_("Target"),
        max_length=255,
        null=True,
        blank=True,
    )
    baseline = models.CharField(
        verbose_name=_("Baseline"),
        max_length=255,
        null=True,
        blank=True,
    )
    ram_indicator = models.BooleanField(
        verbose_name=_("RAM Indicator"),
        default=False,
    )
    active = models.BooleanField(verbose_name=_("Active"), default=True)
    view_on_dashboard = models.BooleanField(
        verbose_name=_("View on Dashboard"),
        default=False,
    )

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
            self.code = ''
        super(Indicator, self).save(*args, **kwargs)


class ReportingRequirement(TimeStampedModel):
    TYPE_QPR = "QPR"
    TYPE_HR = "HR"
    TYPE_CHOICES = (
        (TYPE_QPR, _("Standard Quarterly Progress Report")),
        (TYPE_HR, _("Humanitarian Report")),
    )

    intervention = models.ForeignKey(
        "partners.Intervention",
        on_delete=models.CASCADE,
        verbose_name=_("Intervention"),
        related_name="reporting_requirements"
    )
    start_date = models.DateField(
        null=True,
        verbose_name=_('Start Date')
    )
    end_date = models.DateField(
        null=True,
        verbose_name=_('End Date')
    )
    due_date = models.DateField(verbose_name=_('Due Date'))
    report_type = models.CharField(max_length=50, choices=TYPE_CHOICES)

    class Meta:
        ordering = ("-end_date", )

    def __str__(self):
        return "{} ({}) {}".format(
            self.get_report_type_display,
            self.report_type,
            self.due_date
        )


class SpecialReportingRequirement(TimeStampedModel):
    intervention = models.ForeignKey(
        "partners.Intervention",
        on_delete=models.CASCADE,
        verbose_name=_("Intervention"),
        related_name="special_reporting_requirements"
    )
    description = models.CharField(
        blank=True,
        max_length=256,
        verbose_name=_("Description")
    )
    due_date = models.DateField(verbose_name=_('Due Date'))

    class Meta:
        ordering = ("-due_date", )

    def __str__(self):
        return str(self.due_date)
