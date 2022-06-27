from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from model_utils.models import TimeStampedModel


class BaseLowerResult(TimeStampedModel):
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

    def __str__(self):
        if not self.code:
            return self.name

        return '{}: {}'.format(
            self.code,
            self.name
        )

    class Meta:
        abstract = True
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

    @classmethod
    def renumber_results_for_result_link(cls, result_link):
        results = result_link.ll_results.all()
        # drop codes because in another case we'll face to UniqueViolation exception
        results.update(code=None)
        for i, result in enumerate(results):
            result.code = '{0}.{1}'.format(result_link.code, i + 1)
        cls.objects.bulk_update(results, fields=['code'])


class BaseInterventionTimeFrame(TimeStampedModel):
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
        abstract = True
        ordering = ('intervention', 'start_date',)


class BaseInterventionActivity(TimeStampedModel):
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
        abstract = True
        verbose_name = _('Intervention Activity')
        verbose_name_plural = _('Intervention Activities')
        ordering = ('id',)

    def __str__(self):
        return "{} {}".format(self.result, self.name)

    def update_cash(self):
        items = self.items.all()
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

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = '{0}.{1}'.format(
                self.result.code,
                # explicitly perform model.objects.count to avoid caching
                self.__class__.objects.filter(result=self.result).count() + 1,
            )
        super().save(*args, **kwargs)
        self.result.result_link.intervention.planned_budget.calc_totals()


class BaseInterventionActivityItem(TimeStampedModel):
    activity = models.ForeignKey(
        'reports.InterventionActivity',
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
        abstract = True
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
    def renumber_items_for_activity(cls, activity, start_id=None):
        items = activity.items.all()
        # drop codes because in another case we'll face to UniqueViolation exception
        items.update(code=None)
        for i, item in enumerate(items):
            item.code = '{0}.{1}'.format(activity.code, i + 1)
        cls.objects.bulk_update(items, fields=['code'])
