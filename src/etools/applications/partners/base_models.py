from django.db import models
from django.utils.translation import gettext_lazy as _

from model_utils import Choices
from model_utils.models import TimeStampedModel


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


class BaseInterventionResultLink(TimeStampedModel):
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
            self.intervention, self.code
        )

    def save(self, *args, **kwargs):
        # partner has no access to cp output, so use simplified code calculation
        if not self.code:
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

    # todo: uncomment me after adding planned_budget to base_models
    # def save(self, *args, **kwargs):
    #     self.total_price = self.unit_number * self.unit_price
    #     super().save()
    #     self.intervention.planned_budget.calc_totals()
    #
    # def delete(self, **kwargs):
    #     super().delete(**kwargs)
    #     self.intervention.planned_budget.calc_totals()
