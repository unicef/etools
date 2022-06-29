import decimal
from functools import cached_property

from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from model_utils import Choices, FieldTracker
from model_utils.models import TimeStampedModel
from unicef_djangolib.fields import CurrencyField


class BaseIntervention(TimeStampedModel):
    """
    Represents a partner intervention.

    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`partners.Agreement`
    Relates to :model:`reports.CountryProgramme`
    Relates to :model:`AUTH_USER_MODEL`
    Relates to :model:`partners.PartnerStaffMember`
    Relates to :model:`reports.Office`
    """

    RATING_NONE = "none"
    RATING_MARGINAL = "marginal"
    RATING_SIGNIFICANT = "significant"
    RATING_PRINCIPAL = "principal"
    RATING_CHOICES = (
        (RATING_NONE, "None"),
        (RATING_MARGINAL, "Marginal"),
        (RATING_SIGNIFICANT, "Significant"),
        (RATING_PRINCIPAL, "Principal"),
    )

    title = models.CharField(verbose_name=_("Document Title"), max_length=256)

    # dates
    start = models.DateField(
        verbose_name=_("Start Date"),
        null=True,
        blank=True,
        help_text='The date the Intervention will start'
    )
    end = models.DateField(
        verbose_name=_("End Date"),
        null=True,
        blank=True,
        help_text='The date the Intervention will end'
    )
    reference_number_year = models.IntegerField(null=True)

    context = models.TextField(
        verbose_name=_("Context"),
        blank=True,
        null=True,
    )
    implementation_strategy = models.TextField(
        verbose_name=_("Implementation Strategy"),
        blank=True,
        null=True,
    )

    capacity_development = models.TextField(
        verbose_name=_("Capacity Development"),
        blank=True,
        null=True,
    )
    other_info = models.TextField(
        verbose_name=_("Other Info"),
        blank=True,
        null=True,
    )
    other_partners_involved = models.TextField(
        verbose_name=_("Other Partners Involved"),
        blank=True,
        null=True,
    )

    gender_rating = models.CharField(
        verbose_name=_("Gender Rating"),
        max_length=50,
        choices=RATING_CHOICES,
        default=RATING_NONE,
    )
    gender_narrative = models.TextField(
        verbose_name=_("Gender Narrative"),
        blank=True,
        null=True,
    )
    equity_rating = models.CharField(
        verbose_name=_("Equity Rating"),
        max_length=50,
        choices=RATING_CHOICES,
        default=RATING_NONE,
    )
    equity_narrative = models.TextField(
        verbose_name=_("Equity Narrative"),
        blank=True,
        null=True,
    )
    sustainability_rating = models.CharField(
        verbose_name=_("Sustainability Rating"),
        max_length=50,
        choices=RATING_CHOICES,
        default=RATING_NONE,
    )
    sustainability_narrative = models.TextField(
        verbose_name=_("Sustainability Narrative"),
        blank=True,
        null=True,
    )

    class Meta:
        abstract = True
        ordering = ['-created']

    def __str__(self):
        return '{}'.format(
            self.title
        )

    @cached_property
    def total_partner_contribution(self):
        return self.planned_budget.partner_contribution_local

    @property
    def partner_contribution_percent(self):
        if self.total_local == 0:
            return 0
        return self.total_partner_contribution_local / self.total_local * 100

    @cached_property
    def total_unicef_cash(self):
        return self.planned_budget.unicef_cash_local

    @cached_property
    def total_in_kind_amount(self):
        return self.planned_budget.in_kind_amount_local

    @cached_property
    def total_budget(self):
        return self.total_unicef_cash + self.total_partner_contribution + self.total_in_kind_amount

    @cached_property
    def total_unicef_budget(self):
        return self.total_unicef_cash + self.total_in_kind_amount


class BaseInterventionResultLink(TimeStampedModel):
    cp_output = None  # just dummy to unify logic
    code = models.CharField(verbose_name=_("Code"), max_length=50, blank=True, null=True)
    intervention = models.ForeignKey(
        'partners.Intervention', related_name='result_links', verbose_name=_('Intervention'),
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True
        # unique_together = ['intervention', 'cp_output']
        ordering = ['created']

    def __str__(self):
        return '{} {}'.format(
            self.intervention, self.cp_output
        )

    def save(self, *args, **kwargs):
        if not self.code:
            if self.cp_output:
                self.code = str(
                    # explicitly perform model.objects.count to avoid caching
                    self.__class__.objects.filter(intervention=self.intervention).exclude(cp_output=None).count() + 1,
                )
            else:
                self.code = '0'
        super().save(*args, **kwargs)

    @classmethod
    def renumber_result_links_for_intervention(cls, intervention):
        result_links = intervention.result_links.exclude(cp_output=None)
        # drop codes because in another case we'll face to UniqueViolation exception
        result_links.update(code=None)
        for i, result_link in enumerate(result_links):
            result_link.code = str(i + 1)
        cls.objects.bulk_update(result_links, fields=['code'])


class BaseInterventionRisk(TimeStampedModel):
    RISK_TYPE_ENVIRONMENTAL = "environment"
    RISK_TYPE_FINANCIAL = "financial"
    RISK_TYPE_OPERATIONAL = "operational"
    RISK_TYPE_ORGANIZATIONAL = "organizational"
    RISK_TYPE_POLITICAL = "political"
    RISK_TYPE_STRATEGIC = "strategic"
    RISK_TYPE_SECURITY = "security"
    RISK_TYPE_CHOICES = (
        (RISK_TYPE_ENVIRONMENTAL, "Social & Environmental"),
        (RISK_TYPE_FINANCIAL, "Financial"),
        (RISK_TYPE_OPERATIONAL, "Operational"),
        (RISK_TYPE_ORGANIZATIONAL, "Organizational"),
        (RISK_TYPE_POLITICAL, "Political"),
        (RISK_TYPE_STRATEGIC, "Strategic"),
        (RISK_TYPE_SECURITY, "Safety & security"),
    )

    intervention = models.ForeignKey(
        'partners.Intervention',
        verbose_name=_("Intervention"),
        related_name="risks",
        on_delete=models.CASCADE,
    )
    risk_type = models.CharField(
        verbose_name=_("Risk Type"),
        max_length=50,
        choices=RISK_TYPE_CHOICES,
    )
    mitigation_measures = models.TextField()

    class Meta:
        abstract = True
        ordering = ('id',)

    def __str__(self):
        return "{} {}".format(self.intervention, self.get_risk_type_display())


class BaseInterventionSupplyItem(TimeStampedModel):
    PROVIDED_BY_UNICEF = 'unicef'
    PROVIDED_BY_PARTNER = 'partner'
    PROVIDED_BY_CHOICES = Choices(
        (PROVIDED_BY_UNICEF, _('UNICEF')),
        (PROVIDED_BY_PARTNER, _('Partner')),
    )

    intervention = models.ForeignKey(
        'partners.Intervention',
        verbose_name=_("Intervention"),
        related_name="supply_items",
        on_delete=models.CASCADE,
    )
    title = models.CharField(
        verbose_name=_("Title"),
        max_length=150,
    )
    unit_number = models.DecimalField(
        verbose_name=_("Unit Number"),
        decimal_places=2,
        max_digits=20,
        default=1,
    )
    unit_price = models.DecimalField(
        verbose_name=_("Unit Price"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    result = models.ForeignKey(
        'partners.InterventionResultLink',
        verbose_name=_("Result"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    total_price = models.DecimalField(
        verbose_name=_("Total Price"),
        decimal_places=2,
        max_digits=20,
        blank=True,
        null=True,
    )
    other_mentions = models.TextField(
        verbose_name=_("Other Mentions"),
        blank=True,
    )
    provided_by = models.CharField(
        max_length=10,
        choices=PROVIDED_BY_CHOICES,
        default=PROVIDED_BY_UNICEF,
        verbose_name=_('Provided By'),
    )
    unicef_product_number = models.CharField(
        verbose_name=_("UNICEF Product Number"),
        max_length=150,
        blank=True,
        default="",
    )

    def __str__(self):
        return "{} {}".format(self.intervention, self.title)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.total_price = self.unit_number * self.unit_price
        super().save()
        self.intervention.planned_budget.calc_totals()

    def delete(self, **kwargs):
        super().delete(**kwargs)
        self.intervention.planned_budget.calc_totals()


class BaseInterventionBudget(TimeStampedModel):
    """
    Represents a budget for the intervention
    """
    intervention = models.OneToOneField('partners.Intervention', related_name='planned_budget', null=True, blank=True,
                                        verbose_name=_('Intervention'), on_delete=models.CASCADE)

    # legacy values
    partner_contribution = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                               verbose_name=_('Partner Contribution'))
    unicef_cash = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name=_('Unicef Cash'))
    in_kind_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('UNICEF Supplies')
    )
    total = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_('Total'))

    # sum of all activity/management budget cso/partner values
    partner_contribution_local = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                                     verbose_name=_('Partner Contribution Local'))
    # sum of partner supply items (InterventionSupplyItem)
    partner_supply_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('Partner Supplies Local')
    )
    total_partner_contribution_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('Total Partner Contribution')
    )
    # sum of all activity/management budget unicef values
    total_unicef_cash_local_wo_hq = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('Total HQ Cash Local')
    )
    total_hq_cash_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('Total HQ Cash Local')
    )
    # unicef cash including headquarters contribution
    unicef_cash_local = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                            verbose_name=_('Unicef Cash Local'))
    # sum of unicef supply items (InterventionSupplyItem)
    in_kind_amount_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('UNICEF Supplies Local')
    )
    currency = CurrencyField(verbose_name=_('Currency'), null=False, default='')
    total_local = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_('Total Local'))
    programme_effectiveness = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name=_("Programme Effectiveness (%)"),
        default=0,
    )

    tracker = FieldTracker()

    class Meta:
        abstract = True
        verbose_name_plural = _('Intervention budget')

    @property
    def total_supply(self):
        return self.in_kind_amount_local + self.partner_supply_local

    def total_unicef_contribution(self):
        return self.unicef_cash + self.in_kind_amount

    def total_unicef_contribution_local(self):
        return self.unicef_cash_local + self.in_kind_amount_local

    def total_cash_local(self):
        return self.partner_contribution_local + self.unicef_cash_local

    def get_local_currency(self):
        return "USD"

    @transaction.atomic
    def save(self, **kwargs):
        """
        Calculate total budget on save
        """
        self.calc_totals(save=False)

        # attempt to set default currency
        if not self.currency:
            try:
                self.currency = self.get_local_currency()
            except AttributeError:
                self.currency = "USD"

        super().save(**kwargs)

    def __str__(self):
        # self.total is None if object hasn't been saved yet
        total_local = self.total_local if self.total_local else decimal.Decimal('0.00')
        return '{}: {:.2f}'.format(
            self.intervention,
            total_local
        )

    def calc_totals(self, save=True):
        # partner and unicef totals

        def init_totals():
            self.partner_contribution_local = 0
            self.total_unicef_cash_local_wo_hq = 0

        init = False
        for link in self.intervention.result_links.all():
            for result in link.ll_results.all():
                for activity in result.activities.filter(is_active=True):
                    if not init:
                        init_totals()
                        init = True
                    self.partner_contribution_local += activity.cso_cash
                    self.total_unicef_cash_local_wo_hq += activity.unicef_cash

        programme_effectiveness = 0
        if not init:
            init_totals()
        programme_effectiveness += self.intervention.management_budgets.total
        self.partner_contribution_local += self.intervention.management_budgets.partner_total
        self.total_unicef_cash_local_wo_hq += self.intervention.management_budgets.unicef_total
        self.unicef_cash_local = self.total_unicef_cash_local_wo_hq + self.total_hq_cash_local

        # in kind totals
        self.in_kind_amount_local = 0
        self.partner_supply_local = 0
        for item in self.intervention.supply_items.all():
            if item.provided_by == BaseInterventionSupplyItem.PROVIDED_BY_UNICEF:
                self.in_kind_amount_local += item.total_price
            else:
                self.partner_supply_local += item.total_price

        self.total = self.total_unicef_contribution() + self.partner_contribution
        self.total_partner_contribution_local = self.partner_contribution_local + self.partner_supply_local
        self.total_local = self.total_unicef_contribution_local() + self.total_partner_contribution_local
        if self.total_local:
            self.programme_effectiveness = programme_effectiveness / self.total_local * 100
        else:
            self.programme_effectiveness = 0

        if save:
            self.save()


class BaseInterventionManagementBudget(TimeStampedModel):
    intervention = models.OneToOneField(
        'partners.Intervention',
        verbose_name=_("Intervention"),
        related_name="management_budgets",
        on_delete=models.CASCADE,
    )
    act1_unicef = models.DecimalField(
        verbose_name=_("UNICEF contribution for In-country management and support staff prorated to their contribution to the programme (representation, planning, coordination, logistics, administration, finance)"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    act1_partner = models.DecimalField(
        verbose_name=_("Partner contribution for In-country management and support staff prorated to their contribution to the programme (representation, planning, coordination, logistics, administration, finance)"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    act2_unicef = models.DecimalField(
        verbose_name=_("UNICEF contribution for Operational costs prorated to their contribution to the programme (office space, equipment, office supplies, maintenance)"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    act2_partner = models.DecimalField(
        verbose_name=_("Partner contribution for Operational costs prorated to their contribution to the programme (office space, equipment, office supplies, maintenance)"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    act3_unicef = models.DecimalField(
        verbose_name=_("UNICEF contribution for Planning, monitoring, evaluation and communication, prorated to their contribution to the programme (venue, travels, etc.)"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    act3_partner = models.DecimalField(
        verbose_name=_("Partner contribution for Planning, monitoring, evaluation and communication, prorated to their contribution to the programme (venue, travels, etc.)"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )

    class Meta:
        abstract = True

    @property
    def partner_total(self):
        return self.act1_partner + self.act2_partner + self.act3_partner

    @property
    def unicef_total(self):
        return self.act1_unicef + self.act2_unicef + self.act3_unicef

    @property
    def total(self):
        return self.partner_total + self.unicef_total

    def save(self, *args, **kwargs):
        create = not self.pk
        super().save(*args, **kwargs)
        # planned budget is not created yet, so just skip; totals will be updated during planned budget creation
        if not create:
            self.intervention.planned_budget.calc_totals()

    def update_cash(self):
        aggregated_items = self.items.values('kind').annotate(unicef_cash=Sum('unicef_cash'), cso_cash=Sum('cso_cash'))
        for item in aggregated_items:
            if item['kind'] == BaseInterventionManagementBudgetItem.KIND_CHOICES.in_country:
                self.act1_unicef = item['unicef_cash']
                self.act1_partner = item['cso_cash']
            elif item['kind'] == BaseInterventionManagementBudgetItem.KIND_CHOICES.operational:
                self.act2_unicef = item['unicef_cash']
                self.act2_partner = item['cso_cash']
            elif item['kind'] == BaseInterventionManagementBudgetItem.KIND_CHOICES.planning:
                self.act3_unicef = item['unicef_cash']
                self.act3_partner = item['cso_cash']
        self.save()


class BaseInterventionManagementBudgetItem(models.Model):
    KIND_CHOICES = Choices(
        ('in_country', _('In-country management and support staff prorated to their contribution to the programme '
                         '(representation, planning, coordination, logistics, administration, finance)')),
        ('operational', _('Operational costs prorated to their contribution to the programme '
                          '(office space, equipment, office supplies, maintenance)')),
        ('planning', _('Planning, monitoring, evaluation and communication, '
                       'prorated to their contribution to the programme (venue, travels, etc.)')),
    )

    budget = models.ForeignKey(
        'partners.InterventionManagementBudget', verbose_name=_('Budget'),
        related_name='items', on_delete=models.CASCADE,
    )
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=255,
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
    kind = models.CharField(choices=KIND_CHOICES, verbose_name=_('Kind'), max_length=15)
    unicef_cash = models.DecimalField(
        verbose_name=_("UNICEF Cash Local"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    cso_cash = models.DecimalField(
        verbose_name=_("CSO Cash Local"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.get_kind_display()} - UNICEF: {self.unicef_cash}, CSO: {self.cso_cash}'
