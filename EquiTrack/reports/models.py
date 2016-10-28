from datetime import datetime
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from paintstore.fields import ColorPickerField
from jsonfield import JSONField

from django.utils.functional import cached_property


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


class ResultStructure(models.Model):

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
    OUTCOME = 'Outcome'
    OUTPUT = 'Output'
    ACTIVITY = 'Activity'
    SUBACTIVITY = 'Sub-Activity'

    NAME_CHOICES = (
        (OUTCOME, 'Outcome'),
        (OUTPUT, 'Output'),
        (ACTIVITY, 'Activity'),
        (SUBACTIVITY, 'Sub-Activity'),
    )
    name = models.CharField(max_length=150, unique=True, choices=NAME_CHOICES)

    def __unicode__(self):
        return self.name


class Sector(models.Model):

    name = models.CharField(max_length=45L, unique=True)
    description = models.CharField(
        max_length=256L,
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
        return super(ResultManager, self).get_queryset().select_related('country_programme', 'result_structure', 'result_type')


class Result(MPTTModel):

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


class LowerResult(MPTTModel):

    intervention = models.ForeignKey(to="partners.PCA")
    result_type = models.ForeignKey(ResultType)
    sector = models.ForeignKey(Sector, null=True, blank=True)
    name = models.TextField()
    code = models.CharField(max_length=50, null=True, blank=True)
    quarters = models.ManyToManyField(Quarter, related_name="lowerresults+", blank=True)
    parent = TreeForeignKey(
        'self',
        null=True, blank=True,
        related_name='children',
        db_index=True
    )

    # Lower Activity level attributes
    partner_contribution = models.IntegerField(default=0, null=True, blank=True)
    unicef_cash = models.IntegerField(default=0, null=True, blank=True)
    in_kind_amount = models.IntegerField(default=0, null=True, blank=True)

    def __unicode__(self):
        return u'{}: {}'.format(
            self.code if self.code else self.result_type.name,
            self.name
        )


class Goal(models.Model):

    result_structure = models.ForeignKey(
        ResultStructure, blank=True, null=True, on_delete=models.DO_NOTHING)
    sector = models.ForeignKey(Sector, related_name='goals')
    name = models.CharField(max_length=512L, unique=True)
    description = models.CharField(max_length=512L, blank=True)

    class Meta:
        verbose_name = 'CCC'
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Unit(models.Model):
    type = models.CharField(max_length=45L, unique=True)

    class Meta:
        ordering = ['type']

    def __unicode__(self):
        return self.type


class IndicatorNormalized(models.Model):
    name = models.CharField(max_length=1024)
    unit = models.ForeignKey(Unit, null=True, blank=True)
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
        if not self.code:
            self.code = None
        super(IndicatorNormalized, self).save(*args, **kwargs)


class AppliedIndicator(models.Model):

    indicator = models.ForeignKey(IndicatorNormalized)
    lower_result = models.ForeignKey(LowerResult)

    context_code = models.CharField(max_length=50, null=True, blank=True,
                                    verbose_name="Code in current context")

    target = models.CharField(max_length=255, null=True, blank=True)
    baseline = models.CharField(max_length=255, null=True, blank=True)
    assumptions = models.TextField(null=True, blank=True)

    total = models.IntegerField(null=True, blank=True, default=0,
                                verbose_name="Current Total")
    sector_total = models.IntegerField(null=True, blank=True,
                                       verbose_name="Current Sector Total")

    # variable disaggregation's that may be present in the work plan
    disaggregation_logic = JSONField(null=True)

    class Meta:
        unique_together = (("indicator", "lower_result"),)


class Indicator(models.Model):

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

    in_activity_info = models.BooleanField(default=False)
    activity_info_indicators = models.ManyToManyField(
        'activityinfo.Indicator',
        blank=True
    )

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