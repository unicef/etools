import random
from datetime import date
from string import ascii_lowercase

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q, Sum
from django.utils.functional import cached_property
from django.utils.translation import gettext as _

from model_utils.fields import AutoCreatedField, AutoLastModifiedField
from model_utils.models import TimeStampedModel
from mptt.models import MPTTModel, TreeForeignKey

from etools.applications.locations.models import Location
from etools.applications.users.models import UserProfile


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
        return super().get_queryset().filter(invalid=False)

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
                    super().save(*args, **kwargs)
                    return
        super().save(*args, **kwargs)


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


class Section(TimeStampedModel):
    """
    Represents a section
    """

    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    description = models.CharField(max_length=256, blank=True, null=True, verbose_name=_('Description'))
    alternate_id = models.IntegerField(blank=True, null=True, verbose_name=_('Alternate ID'))
    alternate_name = models.CharField(max_length=255, null=True, default='', verbose_name=_('Alternate Name'))
    dashboard = models.BooleanField(default=False, verbose_name=_('Dashboard'))
    color = models.CharField(max_length=7, null=True, blank=True, verbose_name=_('Color'))
    active = models.BooleanField(default=True, verbose_name=_('Active'))

    class Meta:
        ordering = ['name']
        db_table = 'reports_sector'

    def __str__(self):
        return '{} {}'.format(
            self.alternate_id if self.alternate_id else '',
            self.name
        )


class ResultManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related(
            'country_programme', 'result_type')


class OutputManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(result_type__name=ResultType.OUTPUT).select_related(
            'country_programme', 'result_type')


class Result(MPTTModel):
    """
    Represents a result, wbs is unique

    Relates to :model:`reports.CountryProgramme`
    Relates to :model:`reports.Section`
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
        Section,
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
    humanitarian_marker_code = models.CharField(verbose_name=_("Humanitarian Marker Code"),
                                                max_length=255, blank=True, null=True)
    humanitarian_marker_name = models.CharField(verbose_name=_("Humanitarian Marker Name"),
                                                max_length=255, blank=True, null=True)

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
    programme_area_code = models.CharField(
        verbose_name=_("Programme Area Code"),
        max_length=16,
        null=True,
        blank=True,
    )
    programme_area_name = models.CharField(
        verbose_name=_("Programme Area Name"),
        max_length=255,
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
        return '{} {}: {}'.format(
            self.code if self.code else '',
            self.result_type.name,
            self.name
        )

    @cached_property
    def output_name(self):
        assert self.result_type.name == ResultType.OUTPUT

        return '{}{}{}-[{}]'.format(
            '[Expired] ' if self.expired else '',
            'Special- ' if self.special else '',
            self.name,
            self.wbs
        )

    @cached_property
    def expired(self):
        if not self.to_date:
            return False

        today = date.today()
        return self.to_date < today

    @cached_property
    def special(self):
        return self.country_programme.special if self.country_programme else False

    def __str__(self):
        return '{} {}: {}'.format(
            self.code if self.code else '',
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
        super().save(*args, **kwargs)
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
    code = models.CharField(verbose_name=_("Code"), max_length=50, blank=True, null=True)

    # not being used. does not affect result link budget since d3693d2fbf7b66f5468fefbe4bc2e9685eeb4348
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if not self.code:
            return self.name

        return '{}: {}'.format(
            self.code,
            self.name
        )

    class Meta:
        unique_together = (('result_link', 'code'),)
        ordering = ('created',)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = '{0}.{1}'.format(
                self.result_link.code,
                # explicitly perform model.objects.count to avoid caching
                self.__class__.objects.filter(result_link=self.result_link).count() + 1,
            )
        super().save(*args, **kwargs)
        # update budgets
        self.result_link.intervention.planned_budget.save()

    @classmethod
    def renumber_results_for_result_link(cls, result_link):
        results = result_link.ll_results.all()
        # drop codes because in another case we'll face to UniqueViolation exception
        results.update(code=None)
        for i, result in enumerate(results):
            result.code = '{0}.{1}'.format(result_link.code, i + 1)
        cls.objects.bulk_update(results, fields=['code'])

    def total(self):
        results = self.activities.aggregate(
            total=Sum("unicef_cash", filter=Q(is_active=True)) + Sum("cso_cash", filter=Q(is_active=True)),
        )
        return results["total"] if results["total"] is not None else 0

    def total_cso(self):
        results = self.activities.aggregate(
            total=Sum("cso_cash", filter=Q(is_active=True)),
        )
        return results["total"] if results["total"] is not None else 0

    def total_unicef(self):
        results = self.activities.aggregate(
            total=Sum("unicef_cash", filter=Q(is_active=True)),
        )
        return results["total"] if results["total"] is not None else 0


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
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.title

    def make_copy(self):
        new_code = None
        if self.code:
            # code is unique, so we need to make inherited copy
            new_code = self.code[:40] + '-' + ''.join([random.choice(ascii_lowercase) for _i in range(9)])

        return IndicatorBlueprint.objects.create(
            title=self.title,
            unit=self.unit,
            description=self.description,
            code=new_code,
            subdomain=self.subdomain,
            disaggregatable=self.disaggregatable,
            calculation_formula_across_periods=self.calculation_formula_across_periods,
            calculation_formula_across_locations=self.calculation_formula_across_locations,
            display_type=self.display_type,
        )


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

    def save(self, *args, **kwargs):
        if not self.pk and Disaggregation.objects.filter(name__iexact=self.name).first():
            raise ValidationError("A disaggregation with this name already exists.")
        super().save(*args, **kwargs)


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
    value = models.CharField(max_length=20, verbose_name=_('Value'))
    active = models.BooleanField(default=False, verbose_name=_('Active'))

    def __str__(self):
        return "Disaggregation Value {} -> {}".format(self.disaggregation, self.value)


def indicator_default_dict():
    return {'d': 1, 'v': 0}


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
        Section,
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

    target = models.JSONField(default=indicator_default_dict)
    baseline = models.JSONField(default=indicator_default_dict, null=True)

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

    @cached_property
    def target_display(self):
        ind_type = self.indicator.display_type if self.indicator else None
        numerator = self.target.get('v', self.target)
        denominator = '-'
        if ind_type == IndicatorBlueprint.RATIO:
            denominator = self.target.get('d', '')
        return numerator, denominator

    @cached_property
    def target_display_string(self):
        if self.target_display[1] == '-':
            target = str(self.target_display[0])
        else:
            target = '/'.join(map(str, self.target_display))
        return target

    @cached_property
    def baseline_display(self):
        ind_type = self.indicator.display_type
        if self.baseline is None:
            numerator = None
        else:
            numerator = self.baseline.get('v', self.baseline)
        denominator = '-'
        if ind_type == IndicatorBlueprint.RATIO:
            if self.baseline is None:
                denominator = ''
            else:
                denominator = self.baseline.get('d', '')
        return numerator, denominator

    @cached_property
    def baseline_display_string(self):
        if self.baseline_display[0] is None:
            return _('Unknown')

        if self.baseline_display[1] == '-':
            baseline = str(self.baseline_display[0])
        else:
            baseline = '/'.join(map(str, self.baseline_display))
        return baseline

    class Meta:
        unique_together = (("indicator", "lower_result"),)
        ordering = ("created",)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_amended_name(self):
        return f'{self.indicator}: {self.baseline_display_string} - {self.target_display_string}'

    def make_copy(self):
        indicator_copy = AppliedIndicator.objects.create(
            indicator=self.indicator.make_copy(),
            measurement_specifications=self.measurement_specifications,
            label=self.label,
            numerator_label=self.numerator_label,
            denominator_label=self.denominator_label,
            section=self.section,
            cluster_indicator_id=self.cluster_indicator_id,
            response_plan_name=self.response_plan_name,
            cluster_name=self.cluster_name,
            cluster_indicator_title=self.cluster_indicator_title,
            lower_result=self.lower_result,
            context_code=self.context_code,
            target=self.target,
            baseline=self.baseline,
            assumptions=self.assumptions,
            means_of_verification=self.means_of_verification,
            total=self.total,
            is_high_frequency=self.is_high_frequency,
            is_active=self.is_active,
        )
        indicator_copy.disaggregation.add(*self.disaggregation.all())
        indicator_copy.locations.add(*self.locations.all())
        return indicator_copy


class Indicator(TimeStampedModel):
    """
    Represents an indicator

    Relates to :model:`reports.Unit`
    Relates to :model:`reports.Result`
    """
    # TODO: rename this to RAMIndicator

    sector = models.ForeignKey(
        Section,
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
        return '{}{} {} {}'.format(
            '' if self.active else '[Inactive] ',
            self.name,
            'Baseline: {}'.format(self.baseline) if self.baseline else '',
            'Target: {}'.format(self.target) if self.target else ''
        )

    @property
    def light_repr(self):
        return '{}{}'.format(
            '' if self.active else '[Inactive] ',
            self.name
        )

    def save(self, *args, **kwargs):
        # Prevent from saving empty strings as code because of the unique together constraint
        if not self.code:
            self.code = ''
        super().save(*args, **kwargs)


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
            self.get_report_type_display(),
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


class Office(models.Model):
    """
    Represents an office for the country

    Relates to :model:`AUTH_USER_MODEL`
    """

    name = models.CharField(max_length=254, verbose_name=_('Name'))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name', )


class UserTenantProfile(models.Model):
    profile = models.OneToOneField(
        UserProfile,
        verbose_name=_('Profile'),
        on_delete=models.CASCADE,
        related_name="tenant_profile",
    )
    office = models.ForeignKey(
        "reports.Office",
        null=True,
        blank=True,
        verbose_name=_('Office'),
        on_delete=models.CASCADE,
    )


class InterventionActivity(TimeStampedModel):
    result = models.ForeignKey(
        'reports.LowerResult',
        verbose_name=_("Result"),
        related_name="activities",
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=150,
    )
    code = models.CharField(
        verbose_name=_("Code"),
        max_length=50,
        blank=True,
        null=True
    )
    context_details = models.TextField(
        verbose_name=_("Context Details"),
        blank=True,
        null=True,
    )
    unicef_cash = models.DecimalField(
        verbose_name=_("UNICEF Cash"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    cso_cash = models.DecimalField(
        verbose_name=_("CSO Cash"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )

    time_frames = models.ManyToManyField(
        'InterventionTimeFrame',
        verbose_name=_('Time Frames Enabled'),
        blank=True,
        related_name='activities',
    )

    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Intervention Activity')
        verbose_name_plural = _('Intervention Activities')
        ordering = ('id',)

    def __str__(self):
        return "{} {}".format(self.result, self.name)

    def update_cash(self):
        items = InterventionActivityItem.objects.filter(activity=self)
        items_exists = items.exists()
        if not items_exists:
            return

        aggregates = items.aggregate(
            unicef_cash=Sum('unicef_cash'),
            cso_cash=Sum('cso_cash'),
        )
        self.unicef_cash = aggregates['unicef_cash']
        self.cso_cash = aggregates['cso_cash']
        self.save()

    @property
    def total(self):
        return self.unicef_cash + self.cso_cash

    @property
    def partner_percentage(self):
        if not self.total:
            return 0
        return self.cso_cash / self.total * 100

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = '{0}.{1}'.format(
                self.result.code,
                # explicitly perform model.objects.count to avoid caching
                self.__class__.objects.filter(result=self.result).count() + 1,
            )
        super().save(*args, **kwargs)
        # update budgets
        self.result.result_link.intervention.planned_budget.save()

    @classmethod
    def renumber_activities_for_result(cls, result: LowerResult, start_id=None):
        activities = result.activities.all()
        # drop codes because in another case we'll face to UniqueViolation exception
        activities.update(code=None)
        for i, activity in enumerate(activities):
            activity.code = '{0}.{1}'.format(result.code, i + 1)
        cls.objects.bulk_update(activities, fields=['code'])

    def get_amended_name(self):
        return f'{self.result} {self.name} (Total: {self.total}, UNICEF: {self.unicef_cash}, Partner: {self.cso_cash})'

    def get_time_frames_display(self):
        return ', '.join([f'{tf.start_date.year} Q{tf.quarter}' for tf in self.time_frames.all()])


class InterventionActivityItem(TimeStampedModel):
    activity = models.ForeignKey(
        InterventionActivity,
        verbose_name=_("Activity"),
        related_name="items",
        on_delete=models.CASCADE,
    )
    code = models.CharField(
        verbose_name=_("Code"),
        max_length=50,
        blank=True,
        null=True
    )
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=150,
    )
    unit = models.CharField(
        verbose_name=_("Unit"),
        max_length=150,
    )
    unit_price = models.DecimalField(
        verbose_name=_("Unit Price"),
        decimal_places=2,
        max_digits=20,
    )
    no_units = models.DecimalField(
        verbose_name=_("Units Number"),
        decimal_places=2,
        max_digits=20,
        validators=[MinValueValidator(0)],
    )
    unicef_cash = models.DecimalField(
        verbose_name=_("UNICEF Cash"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    cso_cash = models.DecimalField(
        verbose_name=_("CSO Cash"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )

    class Meta:
        verbose_name = _('Intervention Activity Item')
        verbose_name_plural = _('Intervention Activity Items')
        ordering = ('id',)

    def __str__(self):
        return "{} {}".format(self.activity, self.name)

    def save(self, **kwargs):
        if not self.code:
            self.code = '{0}.{1}'.format(
                self.activity.code,
                # explicitly perform model.objects.count to avoid caching
                self.__class__.objects.filter(activity=self.activity).count() + 1,
            )
        super().save(**kwargs)
        self.activity.update_cash()

    @classmethod
    def renumber_items_for_activity(cls, activity: InterventionActivity, start_id=None):
        items = activity.items.all()
        # drop codes because in another case we'll face to UniqueViolation exception
        items.update(code=None)
        for i, item in enumerate(items):
            item.code = '{0}.{1}'.format(activity.code, i + 1)
        cls.objects.bulk_update(items, fields=['code'])


class InterventionTimeFrame(TimeStampedModel):
    intervention = models.ForeignKey(
        'partners.Intervention',
        verbose_name=_("Intervention"),
        related_name="quarters",
        on_delete=models.CASCADE,
    )
    quarter = models.PositiveSmallIntegerField()
    start_date = models.DateField(
        verbose_name=_("Start Date"),
    )
    end_date = models.DateField(
        verbose_name=_("End Date"),
    )

    def __str__(self):
        return "{} {} - {}".format(
            self.intervention,
            self.start_date,
            self.end_date,
        )

    class Meta:
        ordering = ('intervention', 'start_date',)
