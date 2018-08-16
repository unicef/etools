# -*- coding: utf-8 -*-
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext as _

from model_utils.models import TimeStampedModel
from unicef_djangolib.fields import CurrencyField


class Donor(TimeStampedModel):
    """
    Represents Donor for a Grant.
    """

    name = models.CharField(verbose_name=_("Name"), max_length=45, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class GrantManager(models.Manager):
    def get_queryset(self):
        return super(GrantManager, self).get_queryset().select_related('donor')


class Grant(TimeStampedModel):
    """
    Represents the name of a Grant with expiration date, and Donor name.

    Relates to :model:`funds.Donor`
    """

    donor = models.ForeignKey(
        Donor, verbose_name=_("Donor"),
        on_delete=models.CASCADE,
    )
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=128,
        unique=True
    )
    description = models.CharField(
        verbose_name=_("Description"),
        max_length=255,
        default='',
        blank=True
    )
    expiry = models.DateField(verbose_name=_("Expiry"), null=True, blank=True)

    objects = GrantManager()

    class Meta:
        ordering = ['donor']

    def __str__(self):
        return u"{}: {}".format(
            self.donor.name,
            self.name
        )


class FundsReservationHeader(TimeStampedModel):
    intervention = models.ForeignKey(
        'partners.Intervention',
        verbose_name=_("Reference Number"),
        related_name='frs',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    vendor_code = models.CharField(
        verbose_name=_("Vendor Code"),
        max_length=20,
    )
    fr_number = models.CharField(
        verbose_name=_("FR Number"),
        max_length=20,
        unique=True,
    )
    document_date = models.DateField(
        verbose_name=_("Document Date"),
        null=True,
        blank=True,
    )
    fr_type = models.CharField(
        verbose_name=_("Type"),
        max_length=50,
        default='',
        blank=True,
    )
    currency = CurrencyField(
        verbose_name=_("Currency"),
        max_length=50,
        default='',
        blank=True,
        null=False,
    )
    document_text = models.CharField(
        verbose_name=_("Document Text"),
        max_length=255,
        default='',
        blank=True,
    )

    # this is the field required for validation, this is the 'current_amount'
    intervention_amt = models.DecimalField(
        verbose_name=_('Current FR Amount'),
        default=0,
        max_digits=20,
        decimal_places=2,
    )
    # overall_amount
    total_amt = models.DecimalField(
        verbose_name=_('FR Overall Amount'),
        default=0,
        max_digits=20,
        decimal_places=2,
    )
    # overall_amount
    total_amt_local = models.DecimalField(
        verbose_name=_('FR Overall Amount DC'),
        default=0,
        max_digits=20,
        decimal_places=2,
    )
    # actual is also referred to as "disbursment"
    actual_amt = models.DecimalField(
        verbose_name=_('Actual Cash Transfer'),
        default=0,
        max_digits=20,
        decimal_places=2,
    )
    # actual is also referred to as "disbursment"
    actual_amt_local = models.DecimalField(
        verbose_name=_('Actual Cash Transfer Local'),
        default=0,
        max_digits=20,
        decimal_places=2,
    )
    outstanding_amt = models.DecimalField(
        verbose_name=_('Outstanding DCT'),
        default=0,
        max_digits=20,
        decimal_places=2,
    )
    outstanding_amt_local = models.DecimalField(
        verbose_name=_('Outstanding DCT Local'),
        default=0,
        max_digits=20,
        decimal_places=2,
    )

    start_date = models.DateField(
        verbose_name=_("Start Date"),
        null=True,
        blank=True,
    )
    end_date = models.DateField(
        verbose_name=_("End Date"),
        null=True,
        blank=True,
    )
    multi_curr_flag = models.BooleanField(
        default=False,
        verbose_name=_("Actual and DCT in various currencies"),
    )

    def __str__(self):
        return u'{}'.format(
            self.fr_number
        )

    class Meta:
        ordering = ['fr_number']
        unique_together = ('vendor_code', 'fr_number')

    @property
    def expired(self):
        today = timezone.now().date()
        return self.end_date < today


class FundsReservationItem(TimeStampedModel):
    fund_reservation = models.ForeignKey(
        FundsReservationHeader,
        verbose_name=_("FR Number"),
        related_name="fr_items",
        on_delete=models.CASCADE,
    )
    fr_ref_number = models.CharField(
        verbose_name=_("Item Number"),
        max_length=30,
        default='',
        blank=True,
    )
    line_item = models.PositiveSmallIntegerField(verbose_name=_("Line Item"))
    # grant and fund will be needed for filtering in the future
    wbs = models.CharField(
        verbose_name=_("WBS"),
        max_length=30,
        default='',
        blank=True,
    )
    donor = models.CharField(
        verbose_name=_("Donor Name"),
        max_length=256,
        blank=True,
        null=True,
    )
    donor_code = models.CharField(
        verbose_name=_("Donor Code"),
        max_length=30,
        blank=True,
        null=True,
    )
    grant_number = models.CharField(
        verbose_name=_("Grant Number"),
        max_length=20,
        default='',
        blank=True,
    )
    fund = models.CharField(
        verbose_name=_("Fund"),
        max_length=10,
        default='',
        blank=True,
    )
    overall_amount = models.DecimalField(
        verbose_name=_("Overall Amount"),
        default=0,
        max_digits=20,
        decimal_places=2,
    )
    overall_amount_dc = models.DecimalField(
        verbose_name=_("Overall Amount DC"),
        default=0,
        max_digits=20,
        decimal_places=2,
    )
    due_date = models.DateField(
        verbose_name=_("Due Date"),
        null=True,
        blank=True,
    )
    line_item_text = models.CharField(
        verbose_name=_("Description"),
        max_length=255,
        default='',
        blank=True,
    )

    def __str__(self):
        return u'{}'.format(
            self.fr_ref_number
        )

    class Meta:
        unique_together = ('fund_reservation', 'line_item')
        ordering = ('line_item',)

    def save(self, **kwargs):
        if not self.fr_ref_number:
            self.fr_ref_number = '{}-{}'.format(self.fund_reservation.fr_number, self.line_item)
        return super(FundsReservationItem, self).save(**kwargs)


class FundsCommitmentHeader(TimeStampedModel):
    vendor_code = models.CharField(
        verbose_name=_("Vendor Code"),
        max_length=20,
    )
    fc_number = models.CharField(
        verbose_name=_("Number"),
        max_length=20,
        unique=True,
    )
    document_date = models.DateField(
        verbose_name=_("Document Date"),
        null=True,
        blank=True,
    )
    fc_type = models.CharField(
        verbose_name=_("Type"),
        max_length=50,
        default='',
        blank=True,
    )
    currency = CurrencyField(
        verbose_name=_("Currency"),
        max_length=50,
        default='',
        blank=True,
    )
    document_text = models.CharField(
        verbose_name=_("Document"),
        max_length=255,
        default='',
        blank=True,
    )
    exchange_rate = models.CharField(
        verbose_name=_("Exchange Rate"),
        max_length=20,
        default='',
        blank=True,
    )
    responsible_person = models.CharField(
        verbose_name=_("Responsible"),
        max_length=100,
        blank=True,
        null=True,
    )

    def __str__(self):
        return u'{}'.format(
            self.fc_number
        )


class FundsCommitmentItem(TimeStampedModel):
    fund_commitment = models.ForeignKey(
        FundsCommitmentHeader,
        related_name='fc_items',
        verbose_name=_("Fund Commitment"),
        on_delete=models.CASCADE,
    )
    fc_ref_number = models.CharField(
        verbose_name=_("Number"),
        max_length=30,
        default='',
        blank=True,
    )
    line_item = models.CharField(verbose_name=_("Line Item"), max_length=5)
    wbs = models.CharField(
        verbose_name=_("WBS"),
        max_length=30,
        default='',
        blank=True,
    )
    grant_number = models.CharField(
        verbose_name=_("Grant Number"),
        max_length=20,
        default='',
        blank=True,
    )
    fund = models.CharField(
        verbose_name=_("Fund"),
        max_length=10,
        default='',
        blank=True,
    )
    gl_account = models.CharField(
        verbose_name=_("GL Account"),
        max_length=15,
        default='',
        blank=True,
    )
    due_date = models.DateField(
        verbose_name=_("Due Date"),
        null=True,
        blank=True,
    )
    fr_number = models.CharField(
        verbose_name=_("FR Number"),
        max_length=20,
        blank=True,
        default='',
    )
    commitment_amount = models.DecimalField(
        verbose_name=_("Amount"),
        default=0,
        max_digits=20,
        decimal_places=2,
    )
    commitment_amount_dc = models.DecimalField(
        verbose_name=_("Amount DC"),
        default=0,
        max_digits=20,
        decimal_places=2,
    )
    amount_changed = models.DecimalField(
        verbose_name=_("Amount Changed"),
        default=0,
        max_digits=20,
        decimal_places=2,
    )
    line_item_text = models.CharField(
        verbose_name=_("Description"),
        max_length=255,
        default='',
        blank=True,
    )

    def __str__(self):
        return u'{}'.format(
            self.fc_ref_number
        )

    class Meta:
        unique_together = ('fund_commitment', 'line_item')

    def save(self, **kwargs):
        if not self.fc_ref_number:
            self.fc_ref_number = '{}-{}'.format(self.fund_commitment.fc_number, self.line_item)
        return super(FundsCommitmentItem, self).save(**kwargs)
