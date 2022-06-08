from django.contrib.postgres.fields import ArrayField
from model_utils.models import TimeStampedModel

from django.utils.translation import ugettext_lazy as _
from django.db import models


def get_default_cash_transfer_modalities():
    return [BaseIntervention.CASH_TRANSFER_DIRECT]


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

    CASH_TRANSFER_PAYMENT = "payment"
    CASH_TRANSFER_REIMBURSEMENT = "reimbursement"
    CASH_TRANSFER_DIRECT = "dct"
    CASH_TRANSFER_CHOICES = (
        (CASH_TRANSFER_PAYMENT, "Direct Payment"),
        (CASH_TRANSFER_REIMBURSEMENT, "Reimbursement"),
        (CASH_TRANSFER_DIRECT, "Direct Cash Transfer"),
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

    cash_transfer_modalities = ArrayField(
        models.CharField(
            verbose_name=_("Cash Transfer Modalities"),
            max_length=50,
            choices=CASH_TRANSFER_CHOICES,
        ),
        default=get_default_cash_transfer_modalities,
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
    technical_guidance = models.TextField(
        verbose_name=_("Technical Guidance"),
        blank=True,
        null=True,
    )
    confidential = models.BooleanField(
        verbose_name=_("Confidential"),
        default=False,
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
